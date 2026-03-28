from __future__ import annotations

import re

from reflective_agent.models import ScientificEntity, ScientificQuery

from .sources.pubchem_chebi import PubChemChEBISource


class EntityResolver:
    """Resolves compounds and materials into canonical scientific entities."""

    def __init__(self, pubchem_chebi_source: PubChemChEBISource) -> None:
        self.pubchem_chebi_source = pubchem_chebi_source

    def resolve(self, query: ScientificQuery) -> list[ScientificEntity]:
        candidates = list(query.entity_candidates)
        if not candidates:
            candidates = self._extract_candidates(query.raw_text)
        entities: list[ScientificEntity] = []
        seen: set[str] = set()
        for candidate in candidates:
            for match in self.pubchem_chebi_source.resolve(candidate):
                key = match.canonical_name.casefold()
                if key not in seen:
                    seen.add(key)
                    entities.append(match)
        return entities

    def _extract_candidates(self, text: str) -> list[str]:
        matches = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{0,20}\b", text)
        return [item for item in matches if item.lower() not in {"what", "which", "show", "find", "the"}]

