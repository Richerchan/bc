from __future__ import annotations

from dataclasses import replace

from reflective_agent.models import EvidenceRecord


class UnitNormalizer:
    """Normalizes a narrow set of scientific units into canonical forms."""

    CANONICAL_UNITS = {
        "boiling_point": "K",
        "melting_point": "K",
        "molar_mass": "g/mol",
        "molecular_weight": "g/mol",
        "band_gap": "eV",
        "formation_energy_per_atom": "eV/atom",
        "constant_value": None,
    }

    def normalize_record(self, record: EvidenceRecord, requested_unit: str | None = None) -> EvidenceRecord:
        target_unit = requested_unit or self.CANONICAL_UNITS.get(record.property) or record.unit
        normalized_value, normalized_unit = self.normalize_value(
            record.value,
            record.unit,
            target_unit,
            property_name=record.property,
        )
        return replace(
            record,
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
        )

    def normalize_value(
        self,
        value: float | str | None,
        unit: str,
        target_unit: str,
        *,
        property_name: str,
    ) -> tuple[float | str | None, str]:
        if value is None or isinstance(value, str):
            return value, target_unit or unit
        normalized_unit = self._normalize_unit_text(unit)
        normalized_target = self._normalize_unit_text(target_unit)
        if normalized_unit == normalized_target or not normalized_target:
            return value, target_unit or unit

        if property_name in {"boiling_point", "melting_point"}:
            return self._convert_temperature(value, normalized_unit, normalized_target)

        if property_name in {"molar_mass", "molecular_weight"}:
            return self._convert_molar_mass(value, normalized_unit, normalized_target)

        return value, unit

    def units_compatible(self, unit_a: str, unit_b: str) -> bool:
        group_a = self._unit_group(unit_a)
        group_b = self._unit_group(unit_b)
        return group_a != "unknown" and group_a == group_b

    def _convert_temperature(self, value: float, unit: str, target: str) -> tuple[float, str]:
        kelvin = value
        if unit in {"c", "degc", "celsius"}:
            kelvin = value + 273.15
        elif unit in {"k", "kelvin"}:
            kelvin = value
        if target in {"k", "kelvin"}:
            return kelvin, "K"
        if target in {"c", "degc", "celsius"}:
            return kelvin - 273.15, "C"
        return value, unit

    def _convert_molar_mass(self, value: float, unit: str, target: str) -> tuple[float, str]:
        grams_per_mol = value
        if unit == "kg/mol":
            grams_per_mol = value * 1000.0
        elif unit == "g/mol":
            grams_per_mol = value
        if target == "g/mol":
            return grams_per_mol, "g/mol"
        if target == "kg/mol":
            return grams_per_mol / 1000.0, "kg/mol"
        return value, unit

    def _unit_group(self, unit: str) -> str:
        normalized = self._normalize_unit_text(unit)
        if normalized in {"k", "kelvin", "c", "degc", "celsius"}:
            return "temperature"
        if normalized in {"g/mol", "kg/mol"}:
            return "molar_mass"
        if normalized in {"ev"}:
            return "energy"
        if normalized in {"ev/atom"}:
            return "formation_energy"
        if normalized in {"j/k", "j*s", "j/(mol*k)", "mol^-1"}:
            return "constant"
        return "unknown"

    def _normalize_unit_text(self, unit: str) -> str:
        return unit.strip().lower().replace(" ", "")

