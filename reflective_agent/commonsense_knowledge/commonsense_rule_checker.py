from __future__ import annotations

from collections import defaultdict

from reflective_agent.models import CommonsenseEvidencePack, CommonsenseEvidenceRecord


class CommonSenseRuleChecker:
    """Apply minimum evidence discipline before cognition consumes commonsense inputs."""

    STRUCTURED_PROVENANCE = {"factual_structured", "geo_structured"}

    def evaluate(self, evidence_pack: CommonsenseEvidencePack) -> CommonsenseEvidencePack:
        warnings: list[str] = list(evidence_pack.warnings)
        warnings.extend(self._check_weak_commonsense_not_fact(evidence_pack.records))
        warnings.extend(self._check_generative_prior_blocked(evidence_pack.records))
        warnings.extend(self._check_structured_priority(evidence_pack.records))
        warnings.extend(self._check_geo_and_entity_fact_priority(evidence_pack.records))
        evidence_pack.warnings = self._unique(warnings)
        return evidence_pack

    def _check_weak_commonsense_not_fact(self, records: list[CommonsenseEvidenceRecord]) -> list[str]:
        warnings: list[str] = []
        for record in records:
            if record.provenance_type == "weak_commonsense":
                warnings.append(
                    f"Weak commonsense remains advisory only: {record.entity} {record.relation} from {record.source}."
                )
        return warnings

    def _check_generative_prior_blocked(self, records: list[CommonsenseEvidenceRecord]) -> list[str]:
        warnings: list[str] = []
        for record in records:
            if record.provenance_type == "generative_prior":
                warnings.append(
                    f"Generative prior is blocked from evidence use: {record.entity} {record.relation}."
                )
        return warnings

    def _check_structured_priority(self, records: list[CommonsenseEvidenceRecord]) -> list[str]:
        grouped: dict[tuple[str, str], list[CommonsenseEvidenceRecord]] = defaultdict(list)
        warnings: list[str] = []
        for record in records:
            grouped[(record.entity, record.relation)].append(record)
        for key, items in grouped.items():
            has_structured = any(item.provenance_type in self.STRUCTURED_PROVENANCE for item in items)
            has_weak = any(item.provenance_type == "weak_commonsense" for item in items)
            if has_structured and has_weak:
                warnings.append(
                    f"Structured commonsense must outrank weak commonsense for {key[0]} {key[1]}."
                )
        return warnings

    def _check_geo_and_entity_fact_priority(self, records: list[CommonsenseEvidenceRecord]) -> list[str]:
        grouped: dict[tuple[str, str], list[CommonsenseEvidenceRecord]] = defaultdict(list)
        for record in records:
            grouped[(record.entity, record.relation)].append(record)
        warnings: list[str] = []
        priority_relations = {"country", "capital_of", "located_in", "instance_of", "occupation", "born_in"}
        for key, items in grouped.items():
            if key[1] not in priority_relations:
                continue
            has_structured = any(item.provenance_type in self.STRUCTURED_PROVENANCE for item in items)
            if not has_structured:
                warnings.append(
                    f"Geographic/entity facts require structured sources first: {key[0]} {key[1]}."
                )
        return warnings

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
