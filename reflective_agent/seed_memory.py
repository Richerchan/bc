from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .models import MemoryEpisode, MemoryInfluence, SharedGrowthMemoryRecord


class MemoryBackend(ABC):
    """Inspectable memory backend interface."""

    STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "because",
        "by",
        "for",
        "from",
        "get",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "please",
        "return",
        "show",
        "that",
        "the",
        "this",
        "to",
        "what",
        "which",
        "with",
    }

    @abstractmethod
    def append(self, episode: MemoryEpisode) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_all(self) -> list[MemoryEpisode]:
        raise NotImplementedError

    def retrieve(self, query: str, limit: int = 3) -> list[MemoryEpisode]:
        return [episode for _, episode in self.retrieve_scored(query, limit=limit)]

    def retrieve_scored(self, query: str, limit: int = 3) -> list[tuple[int, MemoryEpisode]]:
        tokens = self._tokenize(query)
        ranked: list[tuple[int, MemoryEpisode]] = []
        for episode in self.load_all():
            haystack = " ".join(
                [
                    episode.input_summary,
                    episode.claim,
                    " ".join(episode.context_tags),
                    " ".join(episode.bias_tags),
                    " ".join(episode.reusable_lessons),
                    " ".join(episode.strategy_tags),
                ]
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                ranked.append((score, episode))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[:limit]

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9_]+", text.lower())
            if len(token) >= 3 and token not in self.STOPWORDS
        }


class JsonFileMemoryBackend(MemoryBackend):
    """Project-local JSON memory backend kept for backward compatibility."""

    def __init__(self, storage_path: str | Path) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def append(self, episode: MemoryEpisode) -> None:
        episodes = self.load_all()
        episodes.append(episode)
        payload = [item.to_dict() for item in episodes]
        self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_all(self) -> list[MemoryEpisode]:
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return [MemoryEpisode.from_dict(item) for item in raw]


class SharedGrowthMemoryBackend(MemoryBackend):
    """Directory-backed shared growth memory using one structured record per file."""

    SCHEMA_NAME = "shared_growth_memory"
    SCHEMA_VERSION = 2
    ALLOWED_VALUE_TYPES = {"preference", "bias_lineage", "correction_lineage", "strategy_hint"}
    SHARED_BIAS_ALLOWLIST = {
        "concept_blending",
        "overclaiming",
        "old_template_reuse",
        "premature_convergence",
        "evidence_gap",
        "hidden_assumption",
        "metacognition_consciousness_confusion",
        "wait_state_awareness_confusion",
    }
    EXCLUDED_SHARED_TAG_PREFIXES = ("task:", "task_goal:", "revision_count:", "memory_scope:")

    def __init__(self, root_dir: str | Path, source_project: str = "reflective-growth-agent") -> None:
        self.root_dir = Path(root_dir)
        self.source_project = source_project
        self.records_dir = self.root_dir / "episodes"
        self.schema_path = self.root_dir / "schema.json"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        if not self.schema_path.exists():
            self.schema_path.write_text(
                json.dumps(
                    {
                        "schema": self.SCHEMA_NAME,
                        "schema_version": self.SCHEMA_VERSION,
                        "record_format": "one_json_file_per_value",
                        "value_types": sorted(self.ALLOWED_VALUE_TYPES),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def append(self, episode: MemoryEpisode) -> None:
        self.append_records(self.extract_records(episode))

    def append_records(self, records: list[SharedGrowthMemoryRecord]) -> None:
        for record in records:
            self.append_record(record)

    def append_record(self, record: SharedGrowthMemoryRecord) -> None:
        record_path = self.records_dir / f"{record.record_id}.json"
        if record_path.exists():
            existing = SharedGrowthMemoryRecord.from_dict(json.loads(record_path.read_text(encoding="utf-8")))
            merged = SharedGrowthMemoryRecord(
                schema_version=self.SCHEMA_VERSION,
                record_id=existing.record_id,
                source_scope=record.source_scope,
                source_project=record.source_project,
                value_type=record.value_type,
                memory_key=record.memory_key,
                value=existing.value if existing.value == record.value else record.value,
                tags=self._unique(existing.tags + record.tags),
                evidence_summary=self._unique(existing.evidence_summary + record.evidence_summary),
                created_at=existing.created_at,
                updated_at=record.updated_at,
                source_projects=self._unique(existing.source_projects + record.source_projects + [record.source_project]),
            )
            record_path.write_text(json.dumps(merged.to_dict(), indent=2), encoding="utf-8")
            return
        record_path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")

    def load_all(self) -> list[MemoryEpisode]:
        episodes: list[MemoryEpisode] = []
        for record in self.load_records():
            episodes.append(
                MemoryEpisode(
                    input_summary=record.value,
                    context_tags=list(record.tags),
                    claim=record.value,
                    evidence_summary=list(record.evidence_summary),
                    fact_items=[],
                    bias_tags=[record.value] if record.value_type == "bias_lineage" else [],
                    correction_actions=[record.value] if record.value_type == "correction_lineage" else [],
                    correction_lineage=[record.value] if record.value_type == "correction_lineage" else [],
                    strategy_tags=[record.value] if record.value_type in {"preference", "strategy_hint"} else [],
                    final_result="",
                    reusable_lessons=[record.value] if record.value_type == "strategy_hint" else [],
                )
            )
        return episodes

    def load_records(self) -> list[SharedGrowthMemoryRecord]:
        records: list[SharedGrowthMemoryRecord] = []
        for record_path in sorted(self.records_dir.glob("*.json")):
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            records.append(SharedGrowthMemoryRecord.from_dict(payload))
        return records

    def retrieve_records(self, query: str, limit: int = 3) -> list[tuple[int, SharedGrowthMemoryRecord]]:
        tokens = self._tokenize(query)
        ranked: list[tuple[int, SharedGrowthMemoryRecord]] = []
        for record in self.load_records():
            haystack = " ".join(
                [
                    record.value,
                    " ".join(record.tags),
                    " ".join(record.evidence_summary),
                    record.value_type,
                ]
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                ranked.append((score, record))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[:limit]

    def extract_records(self, episode: MemoryEpisode) -> list[SharedGrowthMemoryRecord]:
        now = datetime.now(timezone.utc).isoformat()
        records: list[SharedGrowthMemoryRecord] = []

        for preference in self._extract_preferences(episode):
            records.append(self._make_record("preference", preference, episode, now))
        for bias in self._extract_bias_lineage(episode):
            records.append(self._make_record("bias_lineage", bias, episode, now))
        for correction in self._extract_correction_lineage(episode):
            records.append(self._make_record("correction_lineage", correction, episode, now))
        for strategy in self._extract_strategy_hints(episode):
            records.append(self._make_record("strategy_hint", strategy, episode, now))
        return records

    def _make_record(
        self,
        value_type: str,
        value: str,
        episode: MemoryEpisode,
        timestamp: str,
    ) -> SharedGrowthMemoryRecord:
        normalized_value = self._normalize(value)
        memory_key = f"{value_type}:{normalized_value}"
        record_id = str(uuid5(NAMESPACE_URL, memory_key))
        return SharedGrowthMemoryRecord(
            schema_version=self.SCHEMA_VERSION,
            record_id=record_id,
            source_scope="shared_growth",
            source_project=self.source_project,
            value_type=value_type,  # type: ignore[arg-type]
            memory_key=memory_key,
            value=value,
            tags=self._shared_tags(episode),
            evidence_summary=self._shared_evidence(episode),
            created_at=timestamp,
            updated_at=timestamp,
            source_projects=[self.source_project],
        )

    def _extract_preferences(self, episode: MemoryEpisode) -> list[str]:
        preferences: list[str] = []
        for tag in episode.context_tags:
            if tag.startswith("preference:"):
                preferences.append(tag.split(":", 1)[1].replace("_", " "))
        for candidate in episode.strategy_tags + episode.reusable_lessons:
            if candidate.lower().startswith("prefer "):
                preferences.append(candidate)
        return self._unique(item for item in preferences if self._is_shareable_text(item))

    def _extract_bias_lineage(self, episode: MemoryEpisode) -> list[str]:
        return self._unique(
            bias
            for bias in episode.bias_tags
            if bias in self.SHARED_BIAS_ALLOWLIST
        )

    def _extract_correction_lineage(self, episode: MemoryEpisode) -> list[str]:
        candidates = episode.correction_actions + episode.correction_lineage
        return self._unique(
            item
            for item in candidates
            if self._is_shareable_text(item) and not self._looks_project_specific(item)
        )

    def _extract_strategy_hints(self, episode: MemoryEpisode) -> list[str]:
        candidates = episode.strategy_tags + episode.reusable_lessons
        return self._unique(
            item
            for item in candidates
            if self._is_shareable_text(item)
            and not self._looks_project_specific(item)
            and not item.lower().startswith("prefer ")
        )

    def _shared_tags(self, episode: MemoryEpisode) -> list[str]:
        tags = [
            tag
            for tag in episode.context_tags
            if not tag.startswith(self.EXCLUDED_SHARED_TAG_PREFIXES)
        ]
        tags.extend(f"bias:{bias}" for bias in episode.bias_tags if bias in self.SHARED_BIAS_ALLOWLIST)
        return self._unique(tags)

    def _shared_evidence(self, episode: MemoryEpisode) -> list[str]:
        return self._unique(
            item
            for item in episode.evidence_summary
            if self._is_shareable_text(item) and not self._looks_project_specific(item)
        )

    def _is_shareable_text(self, text: str) -> bool:
        lowered = text.lower().strip()
        if not lowered or len(lowered) < 8:
            return False
        if any(prefix in lowered for prefix in ("/", "\\", ".py", ".json", "tmp_dir", "memory_scope:")):
            return False
        if lowered.startswith("result:") or lowered.startswith("input mentions "):
            return False
        return True

    def _looks_project_specific(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            marker in lowered
            for marker in (
                "task_goal:",
                "revision_count:",
                "project-local",
                "shared_growth_memory",
                "memory.json",
            )
        )

    def _normalize(self, text: str) -> str:
        return " ".join(self._tokenize(text))

    def _unique(self, items: object) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered


class SeedMemory:
    """Layered memory facade over project-local and shared-growth backends."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
        *,
        project_backend: MemoryBackend | None = None,
        shared_growth_backend: MemoryBackend | None = None,
    ) -> None:
        if project_backend is None and storage_path is None:
            raise ValueError("SeedMemory requires either storage_path or project_backend.")

        self.project_backend = project_backend or JsonFileMemoryBackend(storage_path)  # type: ignore[arg-type]
        self.shared_growth_backend = shared_growth_backend

    def append(self, episode: MemoryEpisode, layer: str = "project_local") -> None:
        if layer == "project_local":
            self.project_backend.append(episode)
            return
        if layer == "shared_growth":
            if self.shared_growth_backend is None:
                raise ValueError("Shared growth backend is not configured.")
            self.shared_growth_backend.append(episode)
            return
        raise ValueError(f"Unknown memory layer: {layer}")

    def append_project(self, episode: MemoryEpisode) -> None:
        self.project_backend.append(episode)

    def append_shared_growth(self, episode: MemoryEpisode) -> None:
        if self.shared_growth_backend is not None:
            self.shared_growth_backend.append(episode)

    def load_all(self) -> list[MemoryEpisode]:
        return self.project_backend.load_all()

    def load_layer(self, layer: str) -> list[MemoryEpisode]:
        if layer == "project_local":
            return self.project_backend.load_all()
        if layer == "shared_growth":
            return [] if self.shared_growth_backend is None else self.shared_growth_backend.load_all()
        raise ValueError(f"Unknown memory layer: {layer}")

    def retrieve(self, query: str, limit: int = 3) -> list[MemoryEpisode]:
        return self.project_backend.retrieve(query, limit=limit)

    def retrieve_layered(
        self,
        query: str,
        project_limit: int = 3,
        shared_limit: int = 3,
    ) -> dict[str, list[MemoryEpisode]]:
        layered = {"project_local": self.project_backend.retrieve(query, limit=project_limit)}
        layered["shared_growth"] = (
            []
            if self.shared_growth_backend is None
            else self.shared_growth_backend.retrieve(query, limit=shared_limit)
        )
        return layered

    def build_influence(self, query: str, limit: int = 5) -> MemoryInfluence:
        layered_episodes = self.retrieve_layered(query, project_limit=limit, shared_limit=limit)
        project_episodes = layered_episodes["project_local"]
        shared_records: list[SharedGrowthMemoryRecord] = []
        if isinstance(self.shared_growth_backend, SharedGrowthMemoryBackend):
            shared_records = [record for _, record in self.shared_growth_backend.retrieve_records(query, limit=limit)]

        if not project_episodes and not shared_records:
            return MemoryInfluence()

        fact_hints = self._top_values(item for episode in project_episodes for item in episode.fact_items)
        context_hints = self._top_values(item for episode in project_episodes for item in episode.context_tags)
        project_biases = self._top_values(item for episode in project_episodes for item in episode.bias_tags)
        shared_biases = self._top_shared_values(shared_records, "bias_lineage")
        bias_alerts = self._merge_prefer_primary(project_biases, shared_biases)

        project_corrections = self._top_values(
            item for episode in project_episodes for item in episode.correction_actions + episode.correction_lineage
        )
        shared_corrections = self._top_shared_values(shared_records, "correction_lineage")
        correction_hints = self._merge_prefer_primary(project_corrections, shared_corrections)

        project_strategies = self._top_values(
            item for episode in project_episodes for item in episode.strategy_tags + episode.reusable_lessons
        )
        shared_preferences = self._top_shared_values(shared_records, "preference")
        if not shared_preferences and isinstance(self.shared_growth_backend, SharedGrowthMemoryBackend) and shared_records:
            shared_preferences = self._top_shared_values(self.shared_growth_backend.load_records(), "preference")
        shared_strategies = self._top_shared_values(shared_records, "strategy_hint")
        strategy_hints = self._merge_prefer_primary(project_strategies, shared_strategies)

        divergence_triggers = []
        all_biases = project_biases + [item for item in shared_biases if item not in project_biases]
        if "old_template_reuse" in all_biases:
            divergence_triggers.append("Repeated template reuse detected in relevant memory.")
        if sum("concept_blending" in episode.bias_tags for episode in project_episodes) + sum(
            record.value == "concept_blending" for record in shared_records
        ) >= 2:
            divergence_triggers.append("Concept blending recurs across similar prompts.")
        if len(set(episode.claim for episode in project_episodes)) == 1 and len(project_episodes) > 1:
            divergence_triggers.append("Recent matched claims are too similar to each other.")

        return MemoryInfluence(
            fact_hints=fact_hints,
            context_hints=context_hints,
            preference_hints=shared_preferences,
            bias_alerts=bias_alerts,
            correction_hints=correction_hints,
            strategy_hints=self._merge_prefer_primary(strategy_hints, [f"Preference: {item}" for item in shared_preferences]),
            divergence_triggers=divergence_triggers,
            matched_episode_count=len(project_episodes) + len(shared_records),
            project_match_count=len(project_episodes),
            shared_match_count=len(shared_records),
        )

    def _top_values(self, values: list[str] | tuple[str, ...] | object) -> list[str]:
        counter = Counter(value for value in values if value)
        return [value for value, _ in counter.most_common(5)]

    def _top_shared_values(self, records: list[SharedGrowthMemoryRecord], value_type: str) -> list[str]:
        return self._top_values(record.value for record in records if record.value_type == value_type)

    def _merge_prefer_primary(self, primary: list[str], secondary: list[str], limit: int = 5) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for item in primary + secondary:
            key = item.casefold()
            if item and key not in seen:
                seen.add(key)
                merged.append(item)
            if len(merged) >= limit:
                break
        return merged
