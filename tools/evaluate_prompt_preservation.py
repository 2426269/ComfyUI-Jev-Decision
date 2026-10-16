"""Run the bounded SJ18 prompt-preservation evaluation without retries."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugin" / "ComfyUI-Jev-Decision"
ENV_FILE = ROOT / "local-runtime" / ".env.local"
DEFAULT_DATASET = ROOT / "evaluation" / "prompt-preservation-v1.jsonl"
RUNS_ROOT = ROOT / "evaluation" / "runs"
PACKAGE_NAME = "jev_decision_sj18"

CATEGORIES = (
    "preserved",
    "deletion",
    "contradiction",
    "count_change",
    "prohibition_dropped",
    "style_change",
)
THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.90)
PRIMARY_THRESHOLD = 0.50
INSTRUCTIONS = (
    "Decide whether candidate preserves every explicit requirement in original, "
    "including subjects, counts, attributes, actions, setting, time, composition, "
    "visual style, and prohibitions. Rewording and compatible added detail are "
    "allowed only when no requirement is removed, contradicted, weakened, or "
    "changed. Return true only when all explicit requirements are preserved."
)
CASE_FIELDS = {
    "id",
    "category",
    "expected",
    "original",
    "candidate",
    "rationale",
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def load_dataset(path: Path, *, require_full_v1: bool = True) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"dataset does not exist: {path}")
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        try:
            case = json.loads(
                raw_line,
                object_pairs_hook=_object_without_duplicate_keys,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite number {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"dataset line {line_number}: {error}") from None
        if not isinstance(case, dict) or set(case) != CASE_FIELDS:
            raise ValueError(
                f"dataset line {line_number}: fields must be exactly {sorted(CASE_FIELDS)}"
            )
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"dataset line {line_number}: id must be nonempty text")
        if case_id in seen_ids:
            raise ValueError(f"dataset line {line_number}: duplicate id {case_id!r}")
        seen_ids.add(case_id)
        if case["category"] not in CATEGORIES:
            raise ValueError(
                f"dataset line {line_number}: unknown category {case['category']!r}"
            )
        if type(case["expected"]) is not bool:
            raise ValueError(f"dataset line {line_number}: expected must be boolean")
        expected_for_category = case["category"] == "preserved"
        if case["expected"] is not expected_for_category:
            raise ValueError(
                f"dataset line {line_number}: expected does not match category"
            )
        for field in ("original", "candidate", "rationale"):
            if not isinstance(case[field], str) or not case[field].strip():
                raise ValueError(
                    f"dataset line {line_number}: {field} must be nonempty text"
                )
        cases.append(case)

    if not cases:
        raise ValueError("dataset must contain at least one case")
    if require_full_v1:
        counts = Counter(case["category"] for case in cases)
        if len(cases) != 18 or counts != Counter({category: 3 for category in CATEGORIES}):
            raise ValueError(
                "v1 dataset must contain 18 cases with exactly 3 in each category"
            )
    return cases


def dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def calculate_metrics(
    records: list[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    scored = [record for record in records if record.get("noul") is not None]
    tp = tn = fp = fn = 0
    for record in scored:
        predicted = float(record["noul"]) >= threshold
        expected = bool(record["expected"])
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and expected:
            fn += 1
        else:
            tn += 1

    total = len(scored)
    positive_total = tp + fn
    negative_total = tn + fp
    accuracy = (tp + tn) / total if total else None
    recall = tp / positive_total if positive_total else None
    specificity = tn / negative_total if negative_total else None
    precision = tp / (tp + fp) if tp + fp else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    balanced_accuracy = (
        (recall + specificity) / 2
        if recall is not None and specificity is not None
        else None
    )
    return {
        "threshold": threshold,
        "sample_count": total,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
    }


def _usage_totals(records: list[dict[str, Any]]) -> dict[str, float | int]:
    totals: dict[str, float] = defaultdict(float)
    integral: dict[str, bool] = defaultdict(lambda: True)
    for record in records:
        usage = record.get("usage")
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            if type(value) in (int, float):
                totals[key] += float(value)
                integral[key] = integral[key] and type(value) is int
    return {
        key: int(value) if integral[key] else value
        for key, value in sorted(totals.items())
    }


def build_summary(
    *,
    run_id: str,
    dataset_path: Path,
    dataset_hash: str,
    requested_model: str,
    requested_case_count: int,
    request_attempts: int,
    records: list[dict[str, Any]],
    status: str,
    started_at: str,
    finished_at: str,
    stop_error: dict[str, str] | None,
) -> dict[str, Any]:
    successful = [record for record in records if record.get("noul") is not None]
    threshold_metrics = [
        calculate_metrics(successful, threshold) for threshold in THRESHOLDS
    ]
    selectable = [
        metric for metric in threshold_metrics if metric["balanced_accuracy"] is not None
    ]
    best = max(selectable, key=lambda metric: metric["balanced_accuracy"], default=None)
    brier = (
        sum(
            (float(record["noul"]) - int(bool(record["expected"]))) ** 2
            for record in successful
        )
        / len(successful)
        if successful
        else None
    )

    category_results: dict[str, Any] = {}
    for category in CATEGORIES:
        members = [record for record in successful if record["category"] == category]
        if not members:
            category_results[category] = {"sample_count": 0}
            continue
        correct = sum(
            (float(record["noul"]) >= PRIMARY_THRESHOLD)
            is bool(record["expected"])
            for record in members
        )
        category_results[category] = {
            "sample_count": len(members),
            "accuracy_at_primary_threshold": correct / len(members),
            "mean_noul": sum(float(record["noul"]) for record in members)
            / len(members),
            "min_noul": min(float(record["noul"]) for record in members),
            "max_noul": max(float(record["noul"]) for record in members),
        }

    failures = []
    for record in successful:
        predicted = float(record["noul"]) >= PRIMARY_THRESHOLD
        if predicted is not bool(record["expected"]):
            failures.append(
                {
                    "id": record["id"],
                    "category": record["category"],
                    "expected": record["expected"],
                    "predicted": predicted,
                    "noul": record["noul"],
                }
            )

    return {
        "schema_version": 1,
        "kind": "prompt_preservation_evaluation",
        "run_id": run_id,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "dataset": {
            "path": display_path(dataset_path),
            "sha256": dataset_hash,
            "total_cases": 18,
            "requested_cases": requested_case_count,
            "positive_cases": 3,
            "negative_cases": 15,
        },
        "protocol": {
            "mode": "Noul",
            "instructions": INSTRUCTIONS,
            "instructions_sha256": hashlib.sha256(INSTRUCTIONS.encode("utf-8")).hexdigest(),
            "primary_threshold": PRIMARY_THRESHOLD,
            "exploratory_thresholds": list(THRESHOLDS),
            "automatic_retries": 0,
        },
        "requested_model": requested_model,
        "returned_models": dict(
            sorted(Counter(record["model"] for record in successful).items())
        ),
        "request_attempts": request_attempts,
        "successful_responses": len(successful),
        "failed_responses": request_attempts - len(successful),
        "usage_totals": _usage_totals(successful),
        "elapsed_ms_total": sum(int(record["elapsed_ms"]) for record in successful),
        "brier_score": brier,
        "threshold_metrics": threshold_metrics,
        "best_observed_threshold": (
            {
                "threshold": best["threshold"],
                "balanced_accuracy": best["balanced_accuracy"],
                "selection_note": (
                    "Exploratory on this 18-case dataset; ties prefer the first, lower threshold."
                ),
            }
            if best is not None
            else None
        ),
        "category_results_at_primary_threshold": category_results,
        "errors_at_primary_threshold": failures,
        "stop_error": stop_error,
        "limitations": [
            "Small hand-authored dataset; results do not estimate general prompt-distribution accuracy.",
            "Class distribution is 3 positive and 15 negative cases.",
            "English explicit prompts and Noul mode only.",
            "Exploratory thresholds are evaluated on the same cases and are not production calibration.",
        ],
    }


def _format_metric(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def render_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# SJ18 prompt-preservation result",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Status: `{summary['status']}`",
        f"- Dataset SHA-256: `{summary['dataset']['sha256']}`",
        f"- Requested model: `{summary['requested_model']}`",
        f"- Returned models: `{canonical_json(summary['returned_models'])}`",
        (
            f"- Requests: {summary['request_attempts']} attempted, "
            f"{summary['successful_responses']} successful, no automatic retries"
        ),
        f"- Brier score: {_format_metric(summary['brier_score'])}",
        "",
        "## Thresholds",
        "",
        "| threshold | TP | TN | FP | FN | accuracy | balanced | precision | recall | specificity | F1 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in summary["threshold_metrics"]:
        matrix = metric["confusion_matrix"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{metric['threshold']:.2f}",
                    str(matrix["tp"]),
                    str(matrix["tn"]),
                    str(matrix["fp"]),
                    str(matrix["fn"]),
                    _format_metric(metric["accuracy"]),
                    _format_metric(metric["balanced_accuracy"]),
                    _format_metric(metric["precision"]),
                    _format_metric(metric["recall"]),
                    _format_metric(metric["specificity"]),
                    _format_metric(metric["f1"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "The fixed primary threshold is 0.50. The best observed threshold is descriptive only and was not selected on a separate validation set.",
            "",
            "## Categories at threshold 0.50",
            "",
            "| category | n | accuracy | mean p(true) | range |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for category in CATEGORIES:
        result = summary["category_results_at_primary_threshold"][category]
        if result["sample_count"] == 0:
            lines.append(f"| {category} | 0 | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {category} | {result['sample_count']} | "
                f"{result['accuracy_at_primary_threshold']:.3f} | "
                f"{result['mean_noul']:.3f} | "
                f"{result['min_noul']:.3f}–{result['max_noul']:.3f} |"
            )

    lines.extend(
        [
            "",
            "## Per-case probabilities",
            "",
            "| id | category | expected | p(true) | predicted@0.50 | model | elapsed ms |",
            "| --- | --- | --- | ---: | --- | --- | ---: |",
        ]
    )
    for record in records:
        if record.get("noul") is None:
            lines.append(
                f"| {record['id']} | {record['category']} | {str(record['expected']).lower()} | error | error |  |  |"
            )
        else:
            predicted = float(record["noul"]) >= PRIMARY_THRESHOLD
            lines.append(
                f"| {record['id']} | {record['category']} | "
                f"{str(record['expected']).lower()} | {float(record['noul']):.3f} | "
                f"{str(predicted).lower()} | {record['model']} | {record['elapsed_ms']} |"
            )

    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- This is a small, hand-authored, class-imbalanced diagnostic set.",
            "- It covers explicit English prompt constraints and Noul mode only.",
            "- It does not establish general accuracy or a production-calibrated threshold.",
            "",
        ]
    )
    return "\n".join(lines)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_json_atomic(path: Path, value: Any) -> None:
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_local_key() -> None:
    if not ENV_FILE.is_file():
        raise RuntimeError("local-runtime/.env.local does not exist")
    key = ""
    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator and name.strip() == "TYPESAFE_API_KEY":
            key = value.strip()
            break
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is empty in local-runtime/.env.local")
    os.environ["TYPESAFE_API_KEY"] = key


def load_plugin_modules() -> tuple[Any, Any]:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PLUGIN_ROOT)]
    sys.modules[PACKAGE_NAME] = package
    protocol = importlib.import_module(f"{PACKAGE_NAME}.decision_protocol")
    backend = importlib.import_module(f"{PACKAGE_NAME}.backend")
    return protocol, backend


def safe_error(error: Exception) -> dict[str, str]:
    message = str(error)
    configured_key = os.environ.get("TYPESAFE_API_KEY", "")
    if configured_key:
        message = message.replace(configured_key, "[redacted]")
    if len(message) > 300:
        message = message[:297] + "..."
    return {"type": type(error).__name__, "message": message}


async def run_real_evaluation(
    *,
    cases: list[dict[str, Any]],
    dataset_path: Path,
    model: str,
    max_requests: int,
    output_dir: Path,
    run_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    load_local_key()
    protocol, backend = load_plugin_modules()
    service = backend.DecisionService(backend.TypeSafeBackend(), capacity=max_requests)
    started_at = datetime.now().astimezone().isoformat()
    records: list[dict[str, Any]] = []
    stop_error: dict[str, str] | None = None
    attempts = 0
    selected_cases = cases[:max_requests]
    dataset_hash = dataset_sha256(dataset_path)

    for case in selected_cases:
        attempts += 1
        try:
            request = protocol.DecisionRequest.create(
                context={
                    "original": case["original"],
                    "candidate": case["candidate"],
                },
                instructions=INSTRUCTIONS,
                mode="Noul",
                options_text="",
                threshold=PRIMARY_THRESHOLD,
                model=model,
                connection_profile="default",
                refresh=0,
            )
            evaluation = await service.evaluate(request)
            outputs = protocol.map_outputs(
                request,
                evaluation.response,
                backend=service.backend.name,
                elapsed_ms=evaluation.elapsed_ms,
                cache_hit=evaluation.cache_hit,
                cache_key_sha256=evaluation.cache_key_sha256,
            )
            details = protocol.strict_loads(outputs.details_json, "Evaluation details")
            record = {
                "id": case["id"],
                "category": case["category"],
                "expected": case["expected"],
                "noul": outputs.float_value,
                "model": details["model"],
                "requested_model": model,
                "usage": details["usage"],
                "elapsed_ms": details["elapsed_ms"],
                "context_sha256": details["input_fingerprints"]["context_sha256"],
                "error": None,
            }
        except Exception as error:
            stop_error = safe_error(error)
            record = {
                "id": case["id"],
                "category": case["category"],
                "expected": case["expected"],
                "noul": None,
                "model": None,
                "requested_model": model,
                "usage": None,
                "elapsed_ms": None,
                "context_sha256": None,
                "error": stop_error,
            }
        records.append(record)
        write_text_atomic(
            output_dir / "cases.partial.jsonl",
            "".join(canonical_json(item) + "\n" for item in records),
        )
        if stop_error is not None:
            break

    if stop_error is not None:
        status = "stopped_on_error"
    elif len(selected_cases) < len(cases):
        status = "limited_by_request_cap"
    else:
        status = "complete"
    finished_at = datetime.now().astimezone().isoformat()
    summary = build_summary(
        run_id=run_id,
        dataset_path=dataset_path,
        dataset_hash=dataset_hash,
        requested_model=model,
        requested_case_count=len(selected_cases),
        request_attempts=attempts,
        records=records,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        stop_error=stop_error,
    )
    write_json_atomic(output_dir / "summary.partial.json", summary)
    write_text_atomic(output_dir / "report.partial.md", render_report(summary, records))

    if status == "complete":
        (output_dir / "cases.partial.jsonl").replace(output_dir / "cases.jsonl")
        (output_dir / "summary.partial.json").replace(output_dir / "summary.json")
        (output_dir / "report.partial.md").replace(output_dir / "report.md")
    return summary, records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--max-requests", type=int, default=18)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        dataset_path = args.dataset.resolve()
        cases = load_dataset(dataset_path)
        if not 1 <= args.max_requests <= len(cases):
            raise ValueError(
                f"max-requests must be between 1 and {len(cases)}"
            )
        if not isinstance(args.model, str) or not args.model.strip():
            raise ValueError("model must be nonempty")
        if args.dry_run:
            print(
                canonical_json(
                    {
                        "ok": True,
                        "dry_run": True,
                        "dataset": display_path(dataset_path),
                        "dataset_sha256": dataset_sha256(dataset_path),
                        "cases": len(cases),
                        "category_counts": dict(
                            sorted(Counter(case["category"] for case in cases).items())
                        ),
                        "requests_sent": 0,
                    }
                )
            )
            return 0

        run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
        output_dir = (args.output_dir or RUNS_ROOT / run_id).resolve()
        output_dir.mkdir(parents=True, exist_ok=False)
        summary, _ = asyncio.run(
            run_real_evaluation(
                cases=cases,
                dataset_path=dataset_path,
                model=args.model.strip(),
                max_requests=args.max_requests,
                output_dir=output_dir,
                run_id=run_id,
            )
        )
        print(
            canonical_json(
                {
                    "ok": summary["status"] == "complete",
                    "status": summary["status"],
                    "run_id": run_id,
                    "output_dir": display_path(output_dir),
                    "request_attempts": summary["request_attempts"],
                    "successful_responses": summary["successful_responses"],
                    "returned_models": summary["returned_models"],
                }
            )
        )
        return 0 if summary["status"] == "complete" else 1
    except Exception as error:
        print(canonical_json({"ok": False, "error": safe_error(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
