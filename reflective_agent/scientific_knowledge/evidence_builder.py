from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from reflective_agent.models import EvidencePack, EvidenceRecord, ScientificEntity, ScientificQuery

from .constants_provider import ConstantsProvider
from .sources.materials_project import MaterialsProjectSource
from .sources.pubchem_chebi import PubChemChEBISource
from .sources.webbook import NISTWebBookSource
from .unit_normalizer import UnitNormalizer


class EvidenceBuilder:
    """Builds a normalized evidence pack from routed sources."""

    def __init__(
        self,
        *,
        constants_provider: ConstantsProvider,
        unit_normalizer: UnitNormalizer,
        pubchem_chebi_source: PubChemChEBISource,
        nist_webbook_source: NISTWebBookSource,
        materials_project_source: MaterialsProjectSource,
    ) -> None:
        self.constants_provider = constants_provider
        self.unit_normalizer = unit_normalizer
        self.pubchem_chebi_source = pubchem_chebi_source
        self.nist_webbook_source = nist_webbook_source
        self.materials_project_source = materials_project_source

    def build(
        self,
        query: ScientificQuery,
        entities: list[ScientificEntity],
        selected_sources: list[str],
    ) -> EvidencePack:
        records: list[EvidenceRecord] = []
        trace: list[str] = []

        for source_name in selected_sources:
            source_records = self._query_source(source_name, query, entities)
            trace.append(f"source={source_name} hits={len(source_records)}")
            records.extend(source_records)

        normalized_records = [
            self.unit_normalizer.normalize_record(record, query.requested_unit)
            for record in records
        ]
        warnings = self._run_rule_checks(query, normalized_records)

        return EvidencePack(
            query=query,
            entities=entities,
            records=normalized_records,
            warnings=warnings,
            selected_sources=selected_sources,
            routing_trace=trace,
        )

    def _query_source(
        self,
        source_name: str,
        query: ScientificQuery,
        entities: list[ScientificEntity],
    ) -> list[EvidenceRecord]:
        if source_name == "codata_constants":
            return self._query_constants(query)

        entity_names = [entity.canonical_name for entity in entities] or query.entity_candidates
        records: list[EvidenceRecord] = []
        for entity_name in entity_names:
            if source_name == "pubchem_chebi":
                records.extend(self.pubchem_chebi_source.get_property(entity_name, query.property_name))
            elif source_name == "nist_webbook":
                records.extend(self.nist_webbook_source.query(entity_name, query.property_name))
            elif source_name == "materials_project":
                records.extend(self.materials_project_source.query(entity_name, query.property_name))
        return records

    def _query_constants(self, query: ScientificQuery) -> list[EvidenceRecord]:
        for candidate in query.entity_candidates:
            records = self.constants_provider.lookup(candidate)
            if records:
                return records
        return self.constants_provider.lookup(query.raw_text)

    def _run_rule_checks(self, query: ScientificQuery, records: list[EvidenceRecord]) -> list[str]:
        warnings: list[str] = []
        warnings.extend(self._check_unit_consistency(records))
        warnings.extend(self._check_conditions(query, records))
        warnings.extend(self._check_magnitude(records))
        return warnings

    def _check_unit_consistency(self, records: list[EvidenceRecord]) -> list[str]:
        grouped: dict[tuple[str, str], list[EvidenceRecord]] = defaultdict(list)
        for record in records:
            grouped[(record.entity, record.property)].append(record)
        warnings: list[str] = []
        for key, items in grouped.items():
            units = {item.normalized_unit or item.unit for item in items}
            if len(units) <= 1:
                continue
            compatible = all(
                self.unit_normalizer.units_compatible(items[0].normalized_unit or items[0].unit, item.normalized_unit or item.unit)
                for item in items[1:]
            )
            if not compatible:
                warnings.append(f"Unit consistency check: {key[0]} {key[1]} has incompatible units {sorted(units)}.")
        return warnings

    def _check_conditions(self, query: ScientificQuery, records: list[EvidenceRecord]) -> list[str]:
        warnings: list[str] = []
        for record in records:
            if not record.condition:
                continue
            if query.condition:
                for key, value in query.condition.items():
                    if key in record.condition and record.condition[key] != value:
                        warnings.append(
                            f"Condition applicability reminder: {record.entity} {record.property} source condition {record.condition} does not exactly match requested {query.condition}."
                        )
            else:
                warnings.append(
                    f"Condition applicability reminder: {record.entity} {record.property} is reported under {record.condition}."
                )
        return warnings

    def _check_magnitude(self, records: list[EvidenceRecord]) -> list[str]:
        warnings: list[str] = []
        for record in records:
            value = record.normalized_value if isinstance(record.normalized_value, (int, float)) else record.value
            if not isinstance(value, (int, float)):
                continue
            if record.property in {"boiling_point", "melting_point"} and value <= 0:
                warnings.append(f"Basic magnitude check: {record.entity} {record.property} <= 0 K is suspicious.")
            if record.property == "molar_mass" and value <= 0:
                warnings.append(f"Basic magnitude check: {record.entity} molar mass must be positive.")
            if record.property == "band_gap" and not 0 <= value <= 20:
                warnings.append(f"Basic magnitude check: {record.entity} band gap {value} eV is outside expected range.")
            if record.property == "constant_value" and value == 0:
                warnings.append(f"Basic constants check: {record.entity} should not be zero.")
        return warnings

