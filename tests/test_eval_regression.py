import tempfile
import unittest
from pathlib import Path

from evals.benchmark_cases import MINIMAL_EVAL_CASES
from evals.run_evals import evaluate_once
from reflective_agent import Orchestrator


class EvalRegressionTests(unittest.TestCase):
    def test_shared_writeback_filter_keeps_project_only_traces_out(self) -> None:
        case = next(item for item in MINIMAL_EVAL_CASES if item.name == "concept_blending_shared_recovery")

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            shared_growth_dir = Path(tmp_dir) / "shared_growth_memory"
            orchestrator = Orchestrator.with_default_components(
                memory_path,
                shared_growth_path=shared_growth_dir,
                source_project="regression-tests",
            )

            for episode in case.shared_seed:
                orchestrator.seed_memory.append_shared_growth(episode)

            orchestrator.run(case.prompt, case.goal)

            payload_texts = [
                path.read_text(encoding="utf-8")
                for path in sorted(shared_growth_dir.joinpath("episodes").glob("*.json"))
            ]
            combined = "\n".join(payload_texts)

            self.assertNotIn("task_goal:", combined)
            self.assertNotIn("revision_count:", combined)
            self.assertNotIn("memory.json", combined)

    def test_dual_layer_fusion_changes_confidence_and_strategy(self) -> None:
        baseline = evaluate_once()
        local_case = next(
            case
            for case in baseline["local_only"]["cases"]
            if case["name"] == "concept_blending_shared_recovery"
        )
        dual_case = next(
            case
            for case in baseline["dual_layer"]["cases"]
            if case["name"] == "concept_blending_shared_recovery"
        )

        self.assertLess(dual_case["confidence"], local_case["confidence"])
        self.assertGreater(dual_case["shared_match_count"], 0)
        self.assertTrue(
            any("bounded engineering language" in note for note in dual_case["strategy_notes"])
        )

    def test_dual_layer_does_not_worsen_bias_recurrence(self) -> None:
        baseline = evaluate_once()
        local_metrics = baseline["local_only"]["metrics"]
        dual_metrics = baseline["dual_layer"]["metrics"]

        self.assertLessEqual(
            dual_metrics["concept_mixing_rate"],
            local_metrics["concept_mixing_rate"],
        )
        self.assertLessEqual(
            dual_metrics["premature_convergence_rate"],
            local_metrics["premature_convergence_rate"],
        )
        self.assertGreaterEqual(
            dual_metrics["revision_success_rate"],
            local_metrics["revision_success_rate"],
        )


if __name__ == "__main__":
    unittest.main()
