import tempfile
import unittest
from pathlib import Path

from reflective_agent import CommonSenseKnowledgeLayer, Orchestrator
from reflective_agent.mirror_agent import MirrorAgent
from reflective_agent.models import MindState, SelfState


class CommonSenseLayerTests(unittest.TestCase):
    def test_structured_geo_sources_outrank_weak_commonsense(self) -> None:
        layer = CommonSenseKnowledgeLayer()

        result = layer.build_evidence("Paris is in which country?", "Resolve a geographic fact.")

        self.assertIn("geonames", result.evidence_pack.selected_sources)
        self.assertIn("wikidata", result.evidence_pack.selected_sources)
        self.assertEqual(result.evidence_pack.records[0].provenance_type, "geo_structured")
        self.assertEqual(result.evidence_pack.records[0].strength, "strong")
        self.assertTrue(
            any("Structured commonsense must outrank weak commonsense" in warning for warning in result.evidence_pack.warnings)
        )

    def test_conceptnet_relations_stay_weak(self) -> None:
        layer = CommonSenseKnowledgeLayer()

        result = layer.build_evidence("What is a knife used for?", "Resolve a commonsense relation.")

        self.assertEqual(result.evidence_pack.records[0].source, "conceptnet")
        self.assertEqual(result.evidence_pack.records[0].provenance_type, "weak_commonsense")
        self.assertEqual(result.evidence_pack.records[0].strength, "weak")

    def test_orchestrator_injects_commonsense_pack_before_cognition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            orchestrator = Orchestrator.with_default_components(memory_path)

            result = orchestrator.run("Paris is in which country?", "Resolve a geographic fact.")

            self.assertIsNotNone(result.final_state.commonsense_evidence_pack)
            self.assertTrue(result.final_state.commonsense_evidence_pack.has_evidence())
            self.assertIn("Grounded commonsense view", result.final_state.main_claim)
            self.assertIn("stage=commonsense_query", " ".join(result.trace))


class MirrorCommonSenseTests(unittest.TestCase):
    def test_mirror_blocks_weak_commonsense_presented_as_fact(self) -> None:
        layer = CommonSenseKnowledgeLayer()
        pack = layer.build_evidence("What is a knife used for?", "Resolve a commonsense relation.").evidence_pack
        state = MindState(
            current_input="What is a knife used for?",
            task_goal="Resolve a commonsense relation.",
            main_claim="Grounded commonsense view: knife used_for is cutting, based on conceptnet.",
            evidence=["Commonsense weak prior: knife used_for = cutting from conceptnet."],
            hidden_assumptions=[],
            alternative_paths=["Use structured sources before weak priors."],
            confidence=0.82,
            self_risk=[],
            proposed_action="Provide a bounded answer with explicit uncertainty.",
            self_state=SelfState(active_goal="Resolve a commonsense relation."),
            commonsense_evidence_pack=pack,
        )

        verdict = MirrorAgent().review(state)

        self.assertIn("weak_commonsense_as_fact", verdict.issues)
        self.assertEqual(verdict.verdict, "revise")


if __name__ == "__main__":
    unittest.main()
