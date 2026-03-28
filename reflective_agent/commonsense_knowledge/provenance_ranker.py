from __future__ import annotations

from reflective_agent.models import CommonsenseEvidenceRecord


class ProvenanceRanker:
    """Assign source strength so downstream layers can distinguish fact from prior."""

    PRIORITY = {
        "geo_structured": 0,
        "factual_structured": 1,
        "weak_commonsense": 2,
        "reserved_atomic": 3,
        "generative_prior": 4,
    }

    def rank(self, records: list[CommonsenseEvidenceRecord]) -> list[CommonsenseEvidenceRecord]:
        ranked = [self._assign_strength(record) for record in records]
        return sorted(
            ranked,
            key=lambda record: (
                self.PRIORITY[record.provenance_type],
                -record.confidence,
                record.source,
                record.entity,
                record.relation,
            ),
        )

    def _assign_strength(self, record: CommonsenseEvidenceRecord) -> CommonsenseEvidenceRecord:
        if record.provenance_type in {"factual_structured", "geo_structured"}:
            record.strength = "strong" if record.confidence >= 0.8 else "medium"
        elif record.provenance_type == "weak_commonsense":
            record.strength = "weak"
        else:
            record.strength = "blocked"
        return record
