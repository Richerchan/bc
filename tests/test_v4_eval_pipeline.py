from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evals.run_v4_evals import evaluate
from evals.v4_cases import build_all_cases, build_track_a_cases, build_track_b_cases, build_track_c_cases


class V4EvalPipelineTests(unittest.TestCase):
    def test_v4_case_counts_match_plan(self) -> None:
        self.assertEqual(len(build_track_a_cases()), 30)
        self.assertEqual(len(build_track_b_cases()), 36)
        self.assertEqual(len(build_track_c_cases()), 20)
        self.assertEqual(len(build_all_cases()), 86)

    def test_track_c_runner_writes_sequence_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "results"
            payload = evaluate(
                track="C",
                modes=["mindstate_mirror_local_memory"],
                output_dir=output_dir,
            )
            self.assertEqual(payload["case_count"], 20)
            self.assertEqual(payload["run_count"], 20)
            raw_files = sorted((output_dir / "raw" / "C").glob("*.json"))
            self.assertEqual(len(raw_files), 20)
            aggregate_path = output_dir / "aggregate" / "C_summary.json"
            self.assertTrue(aggregate_path.exists())


if __name__ == "__main__":
    unittest.main()
