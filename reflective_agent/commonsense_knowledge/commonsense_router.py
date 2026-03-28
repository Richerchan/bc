from __future__ import annotations

from reflective_agent.models import CommonsenseEntity, CommonsenseQuery


class CommonSenseRouter:
    """Choose the smallest source set while preferring structured fact sources."""

    GEO_RELATIONS = {"country", "capital_of", "located_in", "continent", "population"}
    FACT_RELATIONS = {"instance_of", "occupation", "born_in", "spouse", "head_of_state"}

    def route(self, query: CommonsenseQuery, entities: list[CommonsenseEntity]) -> list[str]:
        sources: list[str] = []
        relation_hints = set(query.relation_hints)
        entity_types = {entity.entity_type for entity in entities}

        if relation_hints & self.GEO_RELATIONS or "place" in entity_types or "city" in entity_types or "country" in entity_types:
            sources.extend(["geonames", "wikidata"])
        elif relation_hints & self.FACT_RELATIONS or entities:
            sources.append("wikidata")
        else:
            sources.append("wikidata")

        if entities or query.intent in {"general_relation", "commonsense_relation"} or not relation_hints:
            sources.append("conceptnet")

        if "causal" in relation_hints or "event_effect" in relation_hints:
            sources.append("atomic_reserved")

        ordered: list[str] = []
        seen: set[str] = set()
        for source in sources + query.source_hints:
            if source and source not in seen:
                seen.add(source)
                ordered.append(source)
        return ordered
