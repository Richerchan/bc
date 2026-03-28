from __future__ import annotations

import re

from reflective_agent.models import CommonsenseEntity, CommonsenseQuery

from .sources.conceptnet import ConceptNetSource
from .sources.geonames import GeoNamesSource
from .sources.wikidata import WikidataSource


class CommonSenseEntityResolver:
    """Resolve real-world entities with structured sources first."""

    STOPWORDS = {
        "what",
        "which",
        "where",
        "who",
        "when",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "in",
        "for",
        "to",
        "tell",
        "me",
    }

    def __init__(
        self,
        *,
        wikidata_source: WikidataSource,
        geonames_source: GeoNamesSource,
        conceptnet_source: ConceptNetSource,
    ) -> None:
        self.wikidata_source = wikidata_source
        self.geonames_source = geonames_source
        self.conceptnet_source = conceptnet_source

    def resolve(self, query: CommonsenseQuery) -> list[CommonsenseEntity]:
        candidates = list(query.entity_candidates) or self._extract_candidates(query.raw_text)
        entities: list[CommonsenseEntity] = []
        seen: set[str] = set()
        for candidate in candidates:
            for match in self.wikidata_source.resolve(candidate) + self.geonames_source.resolve(candidate):
                key = f"{match.canonical_name.casefold()}::{match.entity_type}"
                if key not in seen:
                    seen.add(key)
                    entities.append(match)
            if candidate.casefold() not in seen:
                for match in self.conceptnet_source.resolve(candidate):
                    key = f"{match.canonical_name.casefold()}::{match.entity_type}"
                    if key not in seen:
                        seen.add(key)
                        entities.append(match)
        return entities

    def _extract_candidates(self, text: str) -> list[str]:
        matches = re.findall(r"\b[A-Z][A-Za-z0-9.\-]*(?:\s+[A-Z][A-Za-z0-9.\-]*)*\b", text)
        if matches:
            filtered = [item for item in matches if item.lower() not in self.STOPWORDS]
            if filtered:
                return filtered
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b", text)
        return [token for token in tokens if token.lower() not in self.STOPWORDS]
