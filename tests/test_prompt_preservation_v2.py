from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "evaluate_prompt_preservation_v2.py"
SPEC = importlib.util.spec_from_file_location("prompt_preservation_eval_v2", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class DatasetV2Tests(unittest.TestCase):
    def test_committed_dataset_is_balanced_and_paired(self):
        cases = evaluation.load_dataset(evaluation.DEFAULT_DATASET)
        self.assertEqual(24, len(cases))
        self.assertEqual(12, sum(case["expected"] for case in cases))
        self.assertEqual(12, len({case["pair_id"] for case in cases}))
        for split in evaluation.SPLITS:
            members = [case for case in cases if case["split"] == split]
            self.assertEqual(12, len(members))
            self.assertEqual(6, sum(case["expected"] for case in members))
        for language in evaluation.LANGUAGES:
            self.assertEqual(12, sum(case["language"] == language for case in cases))


class MetricsV2Tests(unittest.TestCase):
    def test_threshold_tie_break_prefers_point_five(self):
        records = [
            {"expected": True, "noul": 0.9} for _ in range(6)
        ] + [
            {"expected": False, "noul": 0.1} for _ in range(6)
        ]
        threshold, metrics = evaluation.select_threshold(records)
        self.assertEqual(0.5, threshold)
        self.assertEqual(19, len(metrics))

    def test_threshold_selection_uses_calibration_probabilities(self):
        records = [
            {"expected": True, "noul": 0.45} for _ in range(6)
        ] + [
            {"expected": False, "noul": 0.20} for _ in range(6)
        ]
        threshold, _ = evaluation.select_threshold(records)
        self.assertEqual(0.45, threshold)

    def test_auroc_counts_ties(self):
        records = [
            {"expected": True, "noul": 0.8},
            {"expected": True, "noul": 0.5},
            {"expected": False, "noul": 0.5},
            {"expected": False, "noul": 0.2},
        ]
        self.assertEqual(0.875, evaluation.auroc(records))

    def test_pair_ranking_uses_positive_minus_negative(self):
        records = [
            {
                "pair_id": "p1",
                "split": "validation",
                "language": "zh",
                "expected": True,
                "noul": 0.7,
            },
            {
                "pair_id": "p1",
                "split": "validation",
                "language": "zh",
                "expected": False,
                "noul": 0.3,
            },
        ]
        result = evaluation.pair_results(records)
        self.assertEqual(1, result["correctly_ranked"])
        self.assertAlmostEqual(0.4, result["minimum_margin"])


if __name__ == "__main__":
    unittest.main()
