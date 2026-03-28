from __future__ import annotations

from reflective_agent.models import (
    CommonsenseEntity,
    CommonsenseEvidencePack,
    CommonsenseEvidenceRecord,
    CommonsenseQuery,
)

from .commonsense_rule_checker import CommonSenseRuleChecker
from .provenance_ranker import ProvenanceRanker
from .sources.atomic import AtomicSource
from .sources.conceptnet import ConceptNetSource
from .sources.geonames import GeoNamesSource
from .sources.wikidata import WikidataSource


class CommonSenseEvidenceBuilder:
    """Build a unified commonsense evidence pack from multiple real-world sources."""

    def __init__(
        self,
        *,
        wikidata_source: WikidataSource,
        geonames_source: GeoNamesSource,
        conceptnet_source: ConceptNetSource,
        atomic_source: AtomicSource,
        rule_checker: CommonSenseRuleChecker,
        provenance_ranker: ProvenanceRanker,
    ) -> None:
        self.wikidata_source = wikidata_source
        self.geonames_source = geonames_source
        self.conceptnet_source = conceptnet_source
        self.atomic_source = atomic_source
        self.rule_checker = rule_checker
        self.provenance_ranker = provenance_ranker

    def build(
        self,
        query: CommonsenseQuery,
        entities: list[CommonsenseEntity],
        selected_sources: list[str],
    ) -> CommonsenseEvidencePack:
        records: list[CommonsenseEvidenceRecord] = []
        trace: list[str] = []
        for source_name in selected_sources:
            source_records = self._query_source(source_name, query, entities)
            trace.append(f"source={source_name} hits={len(source_records)}")
            records.extend(source_records)

        ranked_records = self.provenance_ranker.rank(records)
        evidence_pack = CommonsenseEvidencePack(
            query=query,
            entities=entities,
            records=ranked_records,
            selected_sources=selected_sources,
            routing_trace=trace,
        )
        return self.rule_checker.evaluate(evidence_pack)

    def _query_source(
        self,
        source_name: str,
        query: CommonsenseQuery,
        entities: list[CommonsenseEntity],
    ) -> list[CommonsenseEvidenceRecord]:
        if source_name == "wikidata":
            return self.wikidata_source.query(query, entities)
        if source_name == "geonames":
            return self.geonames_source.query(query, entities)
        if source_name == "conceptnet":
            return self.conceptnet_source.query(query, entities)
        if source_name == "atomic_reserved":
            return self.atomic_source.query(query, entities)
        return []
