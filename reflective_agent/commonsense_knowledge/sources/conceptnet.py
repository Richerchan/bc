from __future__ import annotations

from reflective_agent.models import CommonsenseEntity, CommonsenseEvidenceRecord, CommonsenseQuery

from ..base import load_data_file


class ConceptNetSource:
    """Local weak-prior adapter. Its outputs are never hard facts."""

    def __init__(self) -> None:
        self.data = load_data_file("conceptnet_relations.json")

    def resolve(self, candidate: str) -> list[CommonsenseEntity]:
        payload = self._lookup(candidate)
        if payload is None:
            return []
        return [
            CommonsenseEntity(
                mention=candidate,
                canonical_name=payload["canonical_name"],
                entity_type=payload.get("entity_type", "concept"),
                identifiers={},
                aliases=payload.get("aliases", []),
                source="conceptnet",
                confidence=0.55,
            )
        ]

    def query(
        self,
        query: CommonsenseQuery,
        entities: list[CommonsenseEntity],
    ) -> list[CommonsenseEvidenceRecord]:
        relation_hints = set(query.relation_hints)
        records: list[CommonsenseEvidenceRecord] = []
        candidate_keys = {entity.canonical_name.casefold() for entity in entities}
        candidate_keys.update(candidate.casefold() for candidate in query.entity_candidates)
        if not candidate_keys:
            return []
        for key, payload in self.data.items():
            aliases = {alias.casefold() for alias in payload.get("aliases", [])}
            if key not in candidate_keys and not aliases.intersection(candidate_keys):
                continue
            for fact in payload.get("facts", []):
                relation = fact["relation"]
                if relation_hints and relation not in relation_hints:
                    continue
                records.append(
                    CommonsenseEvidenceRecord(
                        entity=payload["canonical_name"],
                        relation=relation,
                        value=fact["value"],
                        condition=fact.get("condition", {}),
                        source="conceptnet",
                        confidence=fact.get("confidence", 0.45),
                        provenance_type="weak_commonsense",
                        timestamp=payload["timestamp"],
                        identifiers={},
                        notes=["Weak commonsense prior only; do not treat as a hard fact."],
                    )
                )
        return records

    def _lookup(self, candidate: str) -> dict[str, object] | None:
        key = candidate.casefold()
        if key in self.data:
            return self.data[key]
        for payload in self.data.values():
            aliases = [alias.casefold() for alias in payload.get("aliases", [])]
            if key == payload["canonical_name"].casefold() or key in aliases:
                return payload
        return None
