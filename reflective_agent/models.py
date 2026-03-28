from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


VerdictType = Literal["pass", "revise", "retrieve", "wait", "diverge"]
SharedGrowthValueType = Literal["preference", "bias_lineage", "correction_lineage", "strategy_hint"]
ProvenanceType = Literal["local_static", "local_cache", "api_cache", "query_wrapper", "derived"]
CommonsenseProvenanceType = Literal[
    "factual_structured",
    "geo_structured",
    "weak_commonsense",
    "generative_prior",
    "reserved_atomic",
]
CommonsenseStrength = Literal["strong", "medium", "weak", "blocked"]


@dataclass
class SelfState:
    stability: float = 0.7
    uncertainty: float = 0.3
    bias_risk: float = 0.3
    memory_pressure: float = 0.0
    attention_mode: str = "focused"
    active_goal: str = ""
    continuity_notes: list[str] = field(default_factory=list)

    def merge(self, updates: dict[str, Any]) -> "SelfState":
        data = asdict(self)
        for key, value in updates.items():
            if key in data:
                data[key] = value
        return SelfState(**data)


@dataclass
class MemoryInfluence:
    fact_hints: list[str] = field(default_factory=list)
    context_hints: list[str] = field(default_factory=list)
    preference_hints: list[str] = field(default_factory=list)
    bias_alerts: list[str] = field(default_factory=list)
    correction_hints: list[str] = field(default_factory=list)
    strategy_hints: list[str] = field(default_factory=list)
    divergence_triggers: list[str] = field(default_factory=list)
    matched_episode_count: int = 0
    project_match_count: int = 0
    shared_match_count: int = 0

    def has_signal(self) -> bool:
        return any(
            [
                self.fact_hints,
                self.context_hints,
                self.preference_hints,
                self.bias_alerts,
                self.correction_hints,
                self.strategy_hints,
                self.divergence_triggers,
            ]
        )


@dataclass
class ScientificQuery:
    raw_text: str
    normalized_text: str
    query_type: str = "unknown"
    entity_candidates: list[str] = field(default_factory=list)
    property_name: str = "general"
    requested_unit: str | None = None
    condition: dict[str, Any] = field(default_factory=dict)
    source_hints: list[str] = field(default_factory=list)


@dataclass
class ScientificEntity:
    canonical_name: str
    entity_type: str
    identifiers: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    source: str = ""
    confidence: float = 0.0


@dataclass
class EvidenceRecord:
    entity: str
    property: str
    value: float | str | None
    unit: str
    condition: dict[str, Any]
    source: str
    timestamp: str
    confidence: float
    provenance_type: ProvenanceType
    normalized_value: float | str | None = None
    normalized_unit: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class EvidencePack:
    query: ScientificQuery
    entities: list[ScientificEntity] = field(default_factory=list)
    records: list[EvidenceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    selected_sources: list[str] = field(default_factory=list)
    routing_trace: list[str] = field(default_factory=list)

    def has_evidence(self) -> bool:
        return bool(self.records)


@dataclass
class KnowledgeAudit:
    query: ScientificQuery
    entities: list[ScientificEntity]
    selected_sources: list[str]
    evidence_pack: EvidencePack
    trace: list[str] = field(default_factory=list)


@dataclass
class CommonsenseQuery:
    raw_text: str
    normalized_text: str
    entity_candidates: list[str] = field(default_factory=list)
    relation_hints: list[str] = field(default_factory=list)
    intent: str = "general"
    source_hints: list[str] = field(default_factory=list)


@dataclass
class CommonsenseEntity:
    mention: str
    canonical_name: str
    entity_type: str
    identifiers: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    source: str = ""
    confidence: float = 0.0


@dataclass
class CommonsenseEvidenceRecord:
    entity: str
    relation: str
    value: str | None
    condition: dict[str, Any]
    source: str
    confidence: float
    provenance_type: CommonsenseProvenanceType
    timestamp: str
    strength: CommonsenseStrength = "medium"
    identifiers: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class CommonsenseEvidencePack:
    query: CommonsenseQuery
    entities: list[CommonsenseEntity] = field(default_factory=list)
    records: list[CommonsenseEvidenceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    selected_sources: list[str] = field(default_factory=list)
    routing_trace: list[str] = field(default_factory=list)

    def has_evidence(self) -> bool:
        return bool(self.records)

    def records_by_strength(self, strength: CommonsenseStrength) -> list[CommonsenseEvidenceRecord]:
        return [record for record in self.records if record.strength == strength]


@dataclass
class CommonsenseAudit:
    query: CommonsenseQuery
    entities: list[CommonsenseEntity]
    selected_sources: list[str]
    evidence_pack: CommonsenseEvidencePack
    trace: list[str] = field(default_factory=list)


@dataclass
class MindState:
    current_input: str
    task_goal: str
    main_claim: str
    evidence: list[str]
    hidden_assumptions: list[str]
    alternative_paths: list[str]
    confidence: float
    self_risk: list[str]
    proposed_action: str
    self_state: SelfState
    context_tags: list[str] = field(default_factory=list)
    strategy_notes: list[str] = field(default_factory=list)
    memory_influence: MemoryInfluence = field(default_factory=MemoryInfluence)
    evidence_pack: EvidencePack | None = None
    commonsense_evidence_pack: CommonsenseEvidencePack | None = None
    revision_count: int = 0
    retrieved_lessons: list[str] = field(default_factory=list)

    def summary(self) -> str:
        commonsense_summary = "None"
        if self.commonsense_evidence_pack is not None:
            commonsense_summary = str(
                [
                    {
                        "entity": record.entity,
                        "relation": record.relation,
                        "value": record.value,
                        "strength": record.strength,
                        "source": record.source,
                    }
                    for record in self.commonsense_evidence_pack.records
                ]
            )
        return (
            f"Claim: {self.main_claim}\n"
            f"Evidence: {self.evidence}\n"
            f"Assumptions: {self.hidden_assumptions}\n"
            f"Action: {self.proposed_action}\n"
            f"Commonsense: {commonsense_summary}\n"
            f"Memory influence: {asdict(self.memory_influence)}"
        )


@dataclass
class MirrorVerdict:
    verdict: VerdictType
    issues: list[str]
    guidance: list[str]
    self_state_update: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryEpisode:
    input_summary: str
    context_tags: list[str]
    claim: str
    evidence_summary: list[str]
    fact_items: list[str] = field(default_factory=list)
    bias_tags: list[str] = field(default_factory=list)
    correction_actions: list[str] = field(default_factory=list)
    correction_lineage: list[str] = field(default_factory=list)
    strategy_tags: list[str] = field(default_factory=list)
    final_result: str = ""
    reusable_lessons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryEpisode":
        defaults = {
            "input_summary": "",
            "context_tags": [],
            "claim": "",
            "evidence_summary": [],
            "fact_items": [],
            "bias_tags": [],
            "correction_actions": [],
            "correction_lineage": [],
            "strategy_tags": [],
            "final_result": "",
            "reusable_lessons": [],
        }
        defaults.update(payload)
        return cls(**defaults)


@dataclass
class SharedGrowthMemoryRecord:
    schema_version: int
    record_id: str
    source_scope: str
    source_project: str
    value_type: SharedGrowthValueType
    memory_key: str
    value: str
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    evidence_summary: list[str] = field(default_factory=list)
    source_projects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "source_scope": self.source_scope,
            "source_project": self.source_project,
            "value_type": self.value_type,
            "memory_key": self.memory_key,
            "value": self.value,
            "tags": self.tags,
            "evidence_summary": self.evidence_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_projects": self.source_projects,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SharedGrowthMemoryRecord":
        if "episode" in payload:
            episode = MemoryEpisode.from_dict(payload.get("episode", {}))
            correction = (
                episode.correction_lineage
                or episode.correction_actions
                or episode.reusable_lessons
                or ["Legacy shared growth episode."]
            )
            value = correction[0]
            return cls(
                schema_version=payload.get("schema_version", 1),
                record_id=payload.get("record_id", ""),
                source_scope=payload.get("source_scope", "shared_growth"),
                source_project=payload.get("source_project", ""),
                value_type="correction_lineage",
                memory_key=f"legacy:correction_lineage:{value.lower()}",
                value=value,
                tags=episode.bias_tags + episode.context_tags + episode.strategy_tags,
                evidence_summary=episode.evidence_summary,
                created_at=payload.get("created_at", ""),
                updated_at=payload.get("created_at", ""),
                source_projects=[payload.get("source_project", "")] if payload.get("source_project") else [],
            )
        return cls(
            schema_version=payload.get("schema_version", 2),
            record_id=payload.get("record_id", ""),
            source_scope=payload.get("source_scope", "shared_growth"),
            source_project=payload.get("source_project", ""),
            value_type=payload.get("value_type", "strategy_hint"),
            memory_key=payload.get("memory_key", ""),
            value=payload.get("value", ""),
            tags=payload.get("tags", []),
            evidence_summary=payload.get("evidence_summary", []),
            created_at=payload.get("created_at", ""),
            updated_at=payload.get("updated_at", payload.get("created_at", "")),
            source_projects=payload.get("source_projects", []),
        )
