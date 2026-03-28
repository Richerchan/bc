from __future__ import annotations

from reflective_agent.models import CommonsenseEntity, CommonsenseEvidenceRecord, CommonsenseQuery

from ..base import load_data_file


class GeoNamesSource:
    """Local snapshot wrapper for place resolution and geographic facts."""

    def __init__(self) -> None:
        self.data = load_data_file("geonames_places.json")

    def resolve(self, candidate: str) -> list[CommonsenseEntity]:
        payload = self._lookup(candidate)
        if payload is None:
            return []
        return [
            CommonsenseEntity(
                mention=candidate,
                canonical_name=payload["canonical_name"],
                entity_type=payload["entity_type"],
                identifiers={"geonames_id": str(payload["geonames_id"])},
                aliases=payload.get("aliases", []),
                source="geonames",
                confidence=0.95,
            )
        ]

    def query(
        self,
        query: CommonsenseQuery,
        entities: list[CommonsenseEntity],
    ) -> list[CommonsenseEvidenceRecord]:
        relation_hints = set(query.relation_hints)
        records: list[CommonsenseEvidenceRecord] = []
        for entity in entities:
            payload = self._lookup(entity.canonical_name)
            if payload is None:
                continue
            for relation, value in payload.get("facts", {}).items():
                if relation_hints and relation not in relation_hints:
                    continue
                records.append(
                    CommonsenseEvidenceRecord(
                        entity=payload["canonical_name"],
                        relation=relation,
                        value=str(value),
                        condition={},
                        source="geonames",
                        confidence=0.93,
                        provenance_type="geo_structured",
                        timestamp=payload["timestamp"],
                        identifiers={"geonames_id": str(payload["geonames_id"])},
                        notes=["Structured geographic fact from GeoNames adapter."],
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
