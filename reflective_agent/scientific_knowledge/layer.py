from __future__ import annotations

from dataclasses import dataclass, field

from reflective_agent.models import EvidencePack, KnowledgeAudit

from .constants_provider import ConstantsProvider
from .entity_resolver import EntityResolver
from .evidence_builder import EvidenceBuilder
from .query_parser import QueryParser
from .source_router import SourceRouter
from .sources.materials_project import MaterialsProjectSource
from .sources.pubchem_chebi import PubChemChEBISource
from .sources.webbook import NISTWebBookSource
from .unit_normalizer import UnitNormalizer


@dataclass
class KnowledgeLayerResult:
    evidence_pack: EvidencePack
    audit: KnowledgeAudit
    trace: list[str] = field(default_factory=list)


class ScientificKnowledgeLayer:
    """Front-loads scientific parsing, routing, normalization, and evidence building."""

    def __init__(self) -> None:
        pubchem_chebi = PubChemChEBISource()
        self.query_parser = QueryParser()
        self.entity_resolver = EntityResolver(pubchem_chebi)
        self.source_router = SourceRouter()
        self.unit_normalizer = UnitNormalizer()
        self.constants_provider = ConstantsProvider()
        self.evidence_builder = EvidenceBuilder(
            constants_provider=self.constants_provider,
            unit_normalizer=self.unit_normalizer,
            pubchem_chebi_source=pubchem_chebi,
            nist_webbook_source=NISTWebBookSource(),
            materials_project_source=MaterialsProjectSource(),
        )

    def build_evidence(self, current_input: str, task_goal: str) -> KnowledgeLayerResult:
        query = self.query_parser.parse(current_input, task_goal)
        entities = self.entity_resolver.resolve(query)
        selected_sources = self.source_router.route(query, entities)
        evidence_pack = self.evidence_builder.build(query, entities, selected_sources)
        trace = [
            f"stage=query_parse property={query.property_name} type={query.query_type} entities={query.entity_candidates}",
            f"stage=entity_resolve resolved={[entity.canonical_name for entity in entities]}",
            f"stage=source_route selected={selected_sources}",
        ]
        trace.extend(evidence_pack.routing_trace)
        if evidence_pack.warnings:
            trace.append(f"stage=rule_checks warnings={evidence_pack.warnings}")
        audit = KnowledgeAudit(
            query=query,
            entities=entities,
            selected_sources=selected_sources,
            evidence_pack=evidence_pack,
            trace=trace,
        )
        return KnowledgeLayerResult(evidence_pack=evidence_pack, audit=audit, trace=trace)

