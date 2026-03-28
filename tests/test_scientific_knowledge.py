import tempfile
import unittest
from pathlib import Path

from reflective_agent import Orchestrator
from reflective_agent.scientific_knowledge import ScientificKnowledgeLayer


class ScientificKnowledgeLayerTests(unittest.TestCase):
    def test_builds_water_boiling_point_evidence_pack(self) -> None:
        layer = ScientificKnowledgeLayer()
        result = layer.build_evidence(
            "What is the boiling point of water at 1 atm?",
            "Return a grounded physical chemistry answer.",
        )

        self.assertEqual(result.evidence_pack.query.property_name, "boiling_point")
        self.assertIn("nist_webbook", result.evidence_pack.selected_sources)
        self.assertTrue(result.evidence_pack.entities)
        self.assertTrue(result.evidence_pack.records)
        record = result.evidence_pack.records[0]
        self.assertEqual(record.entity, "water")
        self.assertEqual(record.property, "boiling_point")
        self.assertEqual(record.normalized_unit, "K")

    def test_builds_constant_evidence_pack(self) -> None:
        layer = ScientificKnowledgeLayer()
        result = layer.build_evidence(
            "What is the Boltzmann constant?",
            "Return the constant with provenance.",
        )

        self.assertEqual(result.evidence_pack.query.query_type, "constant")
        self.assertEqual(result.evidence_pack.selected_sources, ["codata_constants"])
        self.assertEqual(result.evidence_pack.records[0].entity, "Boltzmann constant")
        self.assertEqual(result.evidence_pack.records[0].provenance_type, "local_static")

    def test_orchestrator_uses_evidence_constrained_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            orchestrator = Orchestrator.with_default_components(memory_path)
            result = orchestrator.run(
                "What is the boiling point of water at 1 atm?",
                "Return a grounded physical chemistry answer.",
            )

            self.assertIsNotNone(result.final_state.evidence_pack)
            assert result.final_state.evidence_pack is not None
            self.assertTrue(result.final_state.evidence_pack.records)
            self.assertIn("Evidence-constrained view", result.final_state.main_claim)
            self.assertIn("water:boiling_point", result.output_text)


if __name__ == "__main__":
    unittest.main()
