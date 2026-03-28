from __future__ import annotations

import json
import unittest
from pathlib import Path

from evals import v6_robustness_assets


class RobustnessAssetsTests(unittest.TestCase):
    def test_bootstrap_interval_bounds_mean(self) -> None:
        lo, hi = v6_robustness_assets._bootstrap_ci([0.0, 1.0, 1.0, 0.0, 1.0], n_boot=200)
        self.assertLessEqual(lo, hi)
        self.assertLessEqual(lo, 0.6)
        self.assertGreaterEqual(hi, 0.6)

    def test_raw_results_can_be_loaded_and_cover_all_tracks(self) -> None:
        payloads = v6_robustness_assets._load_raw_results()
        self.assertTrue(payloads)
        tracks = {payload["case"]["track"] for payload in payloads}
        self.assertEqual(tracks, {"A", "B", "C"})

    def test_representative_case_selection_produces_expected_labels(self) -> None:
        payloads = v6_robustness_assets._load_raw_results()
        records = [v6_robustness_assets._extract_record(p) for p in payloads]
        examples = v6_robustness_assets._select_case_examples(records)
        labels = {row["label"] for row in examples}
        self.assertIn("Direct baseline ignores condition mismatch", labels)
        self.assertIn("Correction lineage constrains later claims", labels)


if __name__ == "__main__":
    unittest.main()
