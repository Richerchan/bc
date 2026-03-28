from __future__ import annotations

from reflective_agent.models import EvidenceRecord

from ..base import load_data_file


class NISTWebBookSource:
    """Minimal local cache / query wrapper for NIST Chemistry WebBook properties."""

    def __init__(self) -> None:
        payload = load_data_file("webbook_properties.json")
        self.records = payload["records"]

    def query(self, entity_name: str, property_name: str) -> list[EvidenceRecord]:
        lowered_entity = entity_name.lower()
        records: list[EvidenceRecord] = []
        for item in self.records:
            if item["entity"].lower() != lowered_entity or item["property"] != property_name:
                continue
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
                    notes=["Returned from local NIST Chemistry WebBook cache."],
                )
            )
        return records

