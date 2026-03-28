from __future__ import annotations

import re
from dataclasses import dataclass, field

from reflective_agent.models import CommonsenseAudit, CommonsenseEvidencePack, CommonsenseQuery

from .commonsense_entity_resolver import CommonSenseEntityResolver
from .commonsense_evidence_builder import CommonSenseEvidenceBuilder
from .commonsense_router import CommonSenseRouter
from .commonsense_rule_checker import CommonSenseRuleChecker
from .provenance_ranker import ProvenanceRanker
from .sources.atomic import AtomicSource
from .sources.conceptnet import ConceptNetSource
from .sources.geonames import GeoNamesSource
from .sources.wikidata import WikidataSource


@dataclass
class CommonSenseLayerResult:
    evidence_pack: CommonsenseEvidencePack
    audit: CommonsenseAudit
    trace: list[str] = field(default_factory=list)


class CommonSenseKnowledgeLayer:
    """Front-load real-world commonsense grounding before reflective cognition."""

    RELATION_HINTS = {
        "capital": "capital_of",
        "country": "country",
        "located": "located_in",
        "location": "located_in",
        "born": "born_in",
        "occupation": "occupation",
        "instance": "instance_of",
        "kind": "instance_of",
        "use": "used_for",
        "used": "used_for",
        "part": "part_of",
        "near": "located_in",
        "city": "located_in",
        "population": "population",
        "cause": "causal",
        "effect": "event_effect",
    }

    def __init__(self) -> None:
        wikidata = WikidataSource()
        geonames = GeoNamesSource()
        conceptnet = ConceptNetSource()
        self.entity_resolver = CommonSenseEntityResolver(
            wikidata_source=wikidata,
            geonames_source=geonames,
            conceptnet_source=conceptnet,
        )
        self.router = CommonSenseRouter()
        self.evidence_builder = CommonSenseEvidenceBuilder(
            wikidata_source=wikidata,
            geonames_source=geonames,
            conceptnet_source=conceptnet,
            atomic_source=AtomicSource(),
            rule_checker=CommonSenseRuleChecker(),
            provenance_ranker=ProvenanceRanker(),
        )

    def build_evidence(self, current_input: str, task_goal: str) -> CommonSenseLayerResult:
        query = self._parse_query(current_input, task_goal)
        entities = self.entity_resolver.resolve(query)
        selected_sources = self.router.route(query, entities)
        evidence_pack = self.evidence_builder.build(query, entities, selected_sources)
        trace = [
            f"stage=commonsense_query intent={query.intent} relations={query.relation_hints} entities={query.entity_candidates}",
            f"stage=commonsense_entity_resolve resolved={[entity.canonical_name for entity in entities]}",
            f"stage=commonsense_route selected={selected_sources}",
        ]
        trace.extend(evidence_pack.routing_trace)
        if evidence_pack.warnings:
            trace.append(f"stage=commonsense_rule_checks warnings={evidence_pack.warnings}")
        audit = CommonsenseAudit(
            query=query,
            entities=entities,
            selected_sources=selected_sources,
            evidence_pack=evidence_pack,
            trace=trace,
        )
        return CommonSenseLayerResult(evidence_pack=evidence_pack, audit=audit, trace=trace)

    def _parse_query(self, current_input: str, task_goal: str) -> CommonsenseQuery:
        normalized = re.sub(r"\s+", " ", current_input.strip().lower())
        relation_hints: list[str] = []
        for token, relation in self.RELATION_HINTS.items():
            if token in normalized and relation not in relation_hints:
                relation_hints.append(relation)
        intent = "general"
        if any(relation in {"capital_of", "country", "located_in", "population"} for relation in relation_hints):
            intent = "geo_fact"
        elif relation_hints:
            intent = "general_relation"
        entity_candidates = self.entity_resolver._extract_candidates(current_input)
        return CommonsenseQuery(
            raw_text=current_input,
            normalized_text=normalized,
            entity_candidates=entity_candidates,
            relation_hints=relation_hints,
            intent=intent,
            source_hints=[],
        )
