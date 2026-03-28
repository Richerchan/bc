from __future__ import annotations

from reflective_agent.models import EvidenceRecord

from ..base import load_data_file


class MaterialsProjectSource:
    """Minimal local cache / query wrapper for Materials Project properties."""

    def __init__(self) -> None:
        payload = load_data_file("materials_project_records.json")
        self.records = payload["records"]

    def query(self, entity_name: str, property_name: str) -> list[EvidenceRecord]:
        lowered_entity = entity_name.lower()
        records: list[EvidenceRecord] = []
        for item in self.records:
            if item["entity"].lower() != lowered_entity or item["property"] != property_name:
                continue
            notes = ["Returned from local Materials Project cache."]
            if item.get("condition", {}).get("calculation"):
                notes.append("Calculated property; condition should be checked before using as experimental fact.")
            records.append(
                EvidenceRecord(
                    entity=item["entity"],
                    property=item["property"],
                    value=item["value"],
                    unit=item["unit"],
                    condition=item.get("condition", {}),
                    source=item["source"],
                    timestamp=item["timestamp"],
                    confidence=item["confidence"],
                    provenance_type="local_cache",
                    notes=notes,
                )
            )
        return records

