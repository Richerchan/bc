from __future__ import annotations

from reflective_agent.models import ScientificEntity, ScientificQuery


class SourceRouter:
    """Routes scientific queries to the smallest suitable authority set."""

    PROPERTY_ROUTE = {
        "boiling_point": ["nist_webbook"],
        "melting_point": ["nist_webbook"],
        "molar_mass": ["pubchem_chebi"],
        "molecular_weight": ["pubchem_chebi"],
        "formula": ["pubchem_chebi"],
        "canonical_smiles": ["pubchem_chebi"],
        "iupac_name": ["pubchem_chebi"],
        "band_gap": ["materials_project"],
        "formation_energy_per_atom": ["materials_project"],
        "constant_value": ["codata_constants"],
    }

    def route(self, query: ScientificQuery, entities: list[ScientificEntity]) -> list[str]:
        if query.query_type == "constant":
            return ["codata_constants"]
        if query.property_name in self.PROPERTY_ROUTE:
            return self.PROPERTY_ROUTE[query.property_name]
        if entities:
            entity_types = {entity.entity_type for entity in entities}
            if "material" in entity_types:
                return ["materials_project", "pubchem_chebi"]
            return ["pubchem_chebi", "nist_webbook"]
        return query.source_hints or ["pubchem_chebi"]

