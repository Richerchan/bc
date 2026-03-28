import json
import tempfile
import unittest
from pathlib import Path

from reflective_agent import Orchestrator, resolve_agent_paths


class CliConfigTests(unittest.TestCase):
    def test_resolve_agent_paths_defaults_and_dual_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = resolve_agent_paths(project_root=tmp_dir, mode="dual_layer", source_project="tests")
            self.assertEqual(paths.project_root, Path(tmp_dir).resolve())
            self.assertEqual(paths.project_memory_path, Path(tmp_dir).resolve() / "data" / "memory.json")
            self.assertEqual(paths.shared_growth_path, Path(tmp_dir).resolve() / "data" / "shared_growth_memory")
            self.assertEqual(paths.mode, "dual_layer")
            self.assertEqual(paths.source_project, "tests")

    def test_orchestrator_result_exposes_replayable_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            orchestrator = Orchestrator.with_default_components(memory_path)
            result = orchestrator.run(
                "We can prove consciousness because the system always waits.",
                "Produce a bounded engineering interpretation.",
            )

            self.assertIsNotNone(result.audit)
            assert result.audit is not None
            payload = result.to_dict()
            self.assertIn("audit", payload)
            audit = payload["audit"]
            assert isinstance(audit, dict)
            self.assertIn("memory_influence", audit)
            self.assertIn("knowledge_audit", audit)
            self.assertIn("cycles", audit)
            self.assertIn("final_output", audit)
            self.assertGreaterEqual(len(audit["cycles"]), 1)
            self.assertIn("cognition_state", audit["cycles"][0])
            self.assertIn("mirror_verdict", audit["cycles"][0])
            json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
