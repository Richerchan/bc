from __future__ import annotations

from reflective_agent.models import EvidenceRecord, ScientificEntity

from ..base import load_data_file


class PubChemChEBISource:
    """Project-local cache for entity normalization and basic compound properties."""

    def __init__(self) -> None:
        payload = load_data_file("pubchem_chebi_entities.json")
        self.entities = payload["entities"]

    def resolve(self, name: str) -> list[ScientificEntity]:
        lowered = name.lower()
        matches: list[ScientificEntity] = []
        for item in self.entities:
            aliases = [alias.lower() for alias in item.get("aliases", [])]
            canonical = item["canonical_name"].lower()
            formula = item.get("identifiers", {}).get("formula", "").lower()
            if lowered in aliases or lowered == canonical or lowered == formula:
                matches.append(
                    ScientificEntity(
                        canonical_name=item["canonical_name"],
                        entity_type=item["entity_type"],
                        identifiers=item.get("identifiers", {}),
                        aliases=item.get("aliases", []),
                        source="PubChem / ChEBI (local cache)",
                        confidence=0.96 if lowered == canonical or lowered == formula else 0.9,
                    )
                )
        return matches

    def get_property(self, entity_name: str, property_name: str) -> list[EvidenceRecord]:
        lowered = entity_name.lower()
        records: list[EvidenceRecord] = []
        for item in self.entities:
            aliases = [alias.lower() for alias in item.get("aliases", [])]
            if lowered != item["canonical_name"].lower() and lowered not in aliases:
                continue
            properties = item.get("properties", {})
            prop = properties.get(property_name)
            if prop is None:
                if property_name == "molecular_weight":
                    prop = properties.get("molar_mass")
                elif property_name == "iupac_name":
                    prop = {"value": item["canonical_name"], "unit": "", "source": "PubChem / ChEBI (local cache)", "timestamp": "2025-01-10T00:00:00Z", "confidence": 0.9}
            if prop is None:
                continue
            records.append(
                EvidenceRecord(
                    entity=item["canonical_name"],
                    property="molar_mass" if property_name == "molecular_weight" else property_name,
                    value=prop["value"],
                    unit=prop["unit"],
                    condition={},
                    source=prop["source"],
                    timestamp=prop["timestamp"],
                    confidence=prop["confidence"],
                    provenance_type="local_cache",
                    identifiers=item.get("identifiers", {}),
                    notes=["Entity property returned from local PubChem/ChEBI cache."],
                )
            )
        return records

