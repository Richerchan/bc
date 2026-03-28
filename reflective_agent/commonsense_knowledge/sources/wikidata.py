from __future__ import annotations

from reflective_agent.models import CommonsenseEntity, CommonsenseEvidenceRecord, CommonsenseQuery

from ..base import load_data_file


class WikidataSource:
    """Local snapshot wrapper for structured entity facts and relations."""

    def __init__(self) -> None:
        self.data = load_data_file("wikidata_entities.json")

    def resolve(self, candidate: str) -> list[CommonsenseEntity]:
        payload = self._lookup(candidate)
        if payload is None:
            return []
        return [
            CommonsenseEntity(
                mention=candidate,
                canonical_name=payload["canonical_name"],
                entity_type=payload["entity_type"],
                identifiers={"wikidata_id": payload["wikidata_id"]},
                aliases=payload.get("aliases", []),
                source="wikidata",
                confidence=0.96,
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
                        value=value,
                        condition={},
                        source="wikidata",
                        confidence=0.94,
                        provenance_type="factual_structured",
                        timestamp=payload["timestamp"],
                        identifiers={"wikidata_id": payload["wikidata_id"]},
                        notes=["Structured snapshot fact from Wikidata adapter."],
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
