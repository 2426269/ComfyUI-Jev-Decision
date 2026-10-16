from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "evaluate_prompt_preservation.py"
SPEC = importlib.util.spec_from_file_location("prompt_preservation_eval", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class DatasetTests(unittest.TestCase):
    def test_committed_v1_has_expected_categories_and_labels(self):
        cases = evaluation.load_dataset(evaluation.DEFAULT_DATASET)
        self.assertEqual(18, len(cases))
        self.assertEqual(3, sum(case["expected"] for case in cases))
        self.assertEqual(
            {category: 3 for category in evaluation.CATEGORIES},
            {
                category: sum(case["category"] == category for case in cases)
                for category in evaluation.CATEGORIES
            },
        )

    def test_duplicate_id_is_rejected(self):
        source = evaluation.DEFAULT_DATASET.read_text(encoding="utf-8")
        first = source.splitlines()[0]
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text(first + "\n" + first + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate id"):
                evaluation.load_dataset(path, require_full_v1=False)


class MetricTests(unittest.TestCase):
    def test_confusion_matrix_and_balanced_accuracy(self):
        records = [
            {"expected": True, "noul": 0.9},
            {"expected": True, "noul": 0.2},
            {"expected": False, "noul": 0.8},
            {"expected": False, "noul": 0.1},
        ]
        metric = evaluation.calculate_metrics(records, 0.5)
        self.assertEqual(
            {"tp": 1, "tn": 1, "fp": 1, "fn": 1},
            metric["confusion_matrix"],
        )
        self.assertEqual(0.5, metric["balanced_accuracy"])
        self.assertEqual(0.5, metric["f1"])

    def test_report_uses_ids_without_source_prompts(self):
        records = [
            {
                "id": "preserved-01",
                "category": "preserved",
                "expected": True,
                "noul": 0.9,
                "model": "jev-test",
                "usage": {"input_tokens": 10},
                "elapsed_ms": 12,
            }
        ]
        summary = evaluation.build_summary(
            run_id="test",
            dataset_path=evaluation.DEFAULT_DATASET,
            dataset_hash="0" * 64,
            requested_model="jev-latest",
            requested_case_count=1,
            request_attempts=1,
            records=records,
            status="limited_by_request_cap",
            started_at="2026-09-21T00:00:00+08:00",
            finished_at="2026-09-21T00:00:01+08:00",
            stop_error=None,
        )
        report = evaluation.render_report(summary, records)
        self.assertIn("preserved-01", report)
        self.assertNotIn("Two adult women", report)

    def test_safe_error_redacts_configured_key(self):
        previous = evaluation.os.environ.get("TYPESAFE_API_KEY")
        evaluation.os.environ["TYPESAFE_API_KEY"] = "secret-test-key"
        try:
            result = evaluation.safe_error(RuntimeError("bad secret-test-key"))
        finally:
            if previous is None:
                evaluation.os.environ.pop("TYPESAFE_API_KEY", None)
            else:
                evaluation.os.environ["TYPESAFE_API_KEY"] = previous
        self.assertEqual("bad [redacted]", result["message"])


if __name__ == "__main__":
    unittest.main()
