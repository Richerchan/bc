from __future__ import annotations

from reflective_agent.models import EvidenceRecord

from .base import load_data_file


class ConstantsProvider:
    """Provides local cached CODATA constants."""

    def __init__(self) -> None:
        payload = load_data_file("codata_constants.json")
        self.constants = payload["constants"]

    def lookup(self, constant_name: str) -> list[EvidenceRecord]:
        lowered = constant_name.lower()
        records: list[EvidenceRecord] = []
        for item in self.constants:
            aliases = [alias.lower() for alias in item.get("aliases", [])]
            matched = lowered == item["name"].lower() or lowered in aliases
            if not matched:
                matched = item["name"].lower() in lowered or any(alias in lowered for alias in aliases)
            if matched:
                records.append(
                    EvidenceRecord(
                        entity=item["name"],
                        property=item["property"],
                        value=item["value"],
                        unit=item["unit"],
                        condition={},
                        source=item["source"],
                        timestamp=item["timestamp"],
                        confidence=item["confidence"],
                        provenance_type="local_static",
                        notes=["Authoritative constant loaded from local CODATA cache."],
                    )
                )
        return records
