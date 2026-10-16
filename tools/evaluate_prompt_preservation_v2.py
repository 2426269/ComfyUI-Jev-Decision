"""Run the frozen SJ18-v2 paired prompt-preservation evaluation."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
import evaluate_prompt_preservation as common  # noqa: E402


ROOT = common.ROOT
DEFAULT_DATASET = ROOT / "evaluation" / "prompt-preservation-v2.jsonl"
RUNS_ROOT = ROOT / "evaluation" / "runs" / "v2"
SPLITS = ("calibration", "validation")
LANGUAGES = ("en", "zh")
NEGATIVE_TYPES = (
    "deletion",
    "contradiction",
    "count_or_relation",
    "prohibition_violation",
    "style_or_medium",
    "attribute_scope",
)
THRESHOLD_GRID = tuple(index / 20 for index in range(1, 20))
REFERENCE_THRESHOLD = 0.50
CASE_FIELDS = {
    "id",
    "pair_id",
    "split",
    "language",
    "expected",
    "change_type",
    "original",
    "candidate",
    "rationale",
}


def load_dataset(path: Path, *, require_full_v2: bool = True) -> list[dict[str, Any]]:
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
                object_pairs_hook=common._object_without_duplicate_keys,
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
        for field in ("id", "pair_id", "original", "candidate", "rationale"):
            if not isinstance(case[field], str) or not case[field].strip():
                raise ValueError(
                    f"dataset line {line_number}: {field} must be nonempty text"
                )
        if case["id"] in seen_ids:
            raise ValueError(f"dataset line {line_number}: duplicate id {case['id']!r}")
        seen_ids.add(case["id"])
        if case["split"] not in SPLITS:
            raise ValueError(f"dataset line {line_number}: invalid split")
        if case["language"] not in LANGUAGES:
            raise ValueError(f"dataset line {line_number}: invalid language")
        if type(case["expected"]) is not bool:
            raise ValueError(f"dataset line {line_number}: expected must be boolean")
        allowed_changes = {"preserved", *NEGATIVE_TYPES}
        if case["change_type"] not in allowed_changes:
            raise ValueError(f"dataset line {line_number}: invalid change_type")
        if case["expected"] is not (case["change_type"] == "preserved"):
            raise ValueError(
                f"dataset line {line_number}: expected does not match change_type"
            )
        cases.append(case)

    if not cases:
        raise ValueError("dataset must contain at least one case")
    if not require_full_v2:
        return cases

    if len(cases) != 24:
        raise ValueError("v2 dataset must contain exactly 24 cases")
    if Counter(case["split"] for case in cases) != Counter(
        {"calibration": 12, "validation": 12}
    ):
        raise ValueError("v2 must contain 12 cases in each split")
    if Counter(case["language"] for case in cases) != Counter({"en": 12, "zh": 12}):
        raise ValueError("v2 must contain 12 cases in each language")
    for split in SPLITS:
        members = [case for case in cases if case["split"] == split]
        if Counter(case["expected"] for case in members) != Counter({True: 6, False: 6}):
            raise ValueError(f"{split} must contain 6 positive and 6 negative cases")
        if Counter(
            case["change_type"] for case in members if not case["expected"]
        ) != Counter({change_type: 1 for change_type in NEGATIVE_TYPES}):
            raise ValueError(f"{split} must contain one of each negative change type")
        if Counter(case["language"] for case in members) != Counter({"en": 6, "zh": 6}):
            raise ValueError(f"{split} must contain 6 cases in each language")

    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        pairs[case["pair_id"]].append(case)
    if len(pairs) != 12:
        raise ValueError("v2 must contain exactly 12 pairs")
    for pair_id, members in pairs.items():
        if len(members) != 2 or {member["expected"] for member in members} != {True, False}:
            raise ValueError(f"pair {pair_id!r} must contain one positive and one negative")
        if len({member["original"] for member in members}) != 1:
            raise ValueError(f"pair {pair_id!r} must share the exact original")
        if len({member["split"] for member in members}) != 1:
            raise ValueError(f"pair {pair_id!r} must stay in one split")
        if len({member["language"] for member in members}) != 1:
            raise ValueError(f"pair {pair_id!r} must stay in one language")
        if len({member["candidate"] for member in members}) != 2:
            raise ValueError(f"pair {pair_id!r} candidates must differ")
    return cases


def brier_score(records: list[dict[str, Any]]) -> float | None:
    scored = [record for record in records if record.get("noul") is not None]
    if not scored:
        return None
    return sum(
        (float(record["noul"]) - int(bool(record["expected"]))) ** 2
        for record in scored
    ) / len(scored)


def auroc(records: list[dict[str, Any]]) -> float | None:
    positives = [float(record["noul"]) for record in records if record.get("noul") is not None and record["expected"]]
    negatives = [float(record["noul"]) for record in records if record.get("noul") is not None and not record["expected"]]
    if not positives or not negatives:
        return None
    wins = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives
        for negative in negatives
    )
    return wins / (len(positives) * len(negatives))


def select_threshold(calibration: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]] | tuple[None, list[dict[str, Any]]]:
    successful = [record for record in calibration if record.get("noul") is not None]
    if len(successful) != 12:
        return None, [common.calculate_metrics(successful, threshold) for threshold in THRESHOLD_GRID]
    metrics = [common.calculate_metrics(successful, threshold) for threshold in THRESHOLD_GRID]
    best = max(
        metrics,
        key=lambda metric: (
            metric["balanced_accuracy"],
            -abs(metric["threshold"] - REFERENCE_THRESHOLD),
            -metric["threshold"],
        ),
    )
    return float(best["threshold"]), metrics


def pair_results(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("noul") is not None:
            grouped[record["pair_id"]].append(record)
    pairs = []
    for pair_id in sorted(grouped):
        members = grouped[pair_id]
        if len(members) != 2:
            continue
        positive = next((record for record in members if record["expected"]), None)
        negative = next((record for record in members if not record["expected"]), None)
        if positive is None or negative is None:
            continue
        margin = float(positive["noul"]) - float(negative["noul"])
        pairs.append(
            {
                "pair_id": pair_id,
                "split": positive["split"],
                "language": positive["language"],
                "positive_noul": positive["noul"],
                "negative_noul": negative["noul"],
                "margin": margin,
                "correctly_ranked": margin > 0,
            }
        )
    return {
        "complete_pairs": len(pairs),
        "correctly_ranked": sum(pair["correctly_ranked"] for pair in pairs),
        "mean_margin": sum(pair["margin"] for pair in pairs) / len(pairs) if pairs else None,
        "minimum_margin": min((pair["margin"] for pair in pairs), default=None),
        "pairs": pairs,
    }


def subset_summary(records: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    return {
        "metrics": common.calculate_metrics(records, threshold),
        "brier_score": brier_score(records),
        "auroc": auroc(records),
    }


def usage_totals(records: list[dict[str, Any]]) -> dict[str, float | int]:
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
    model: str,
    records: list[dict[str, Any]],
    attempts: int,
    requested_cases: int,
    status: str,
    started_at: str,
    finished_at: str,
    stop_error: dict[str, str] | None,
) -> dict[str, Any]:
    successful = [record for record in records if record.get("noul") is not None]
    calibration = [record for record in successful if record["split"] == "calibration"]
    validation = [record for record in successful if record["split"] == "validation"]
    selected_threshold, calibration_grid = select_threshold(calibration)
    fixed = {
        "all": subset_summary(successful, REFERENCE_THRESHOLD),
        "calibration": subset_summary(calibration, REFERENCE_THRESHOLD),
        "validation": subset_summary(validation, REFERENCE_THRESHOLD),
    }
    selected = (
        {
            "threshold": selected_threshold,
            "selection_split": "calibration",
            "tie_break": "closest_to_0.50_then_lower",
            "calibration": subset_summary(calibration, selected_threshold),
            "validation": subset_summary(validation, selected_threshold),
        }
        if selected_threshold is not None
        else None
    )
    language_results = {
        language: subset_summary(
            [record for record in successful if record["language"] == language],
            REFERENCE_THRESHOLD,
        )
        for language in LANGUAGES
    }
    negative_types = {}
    for change_type in NEGATIVE_TYPES:
        members = [record for record in successful if record["change_type"] == change_type]
        negative_types[change_type] = {
            "sample_count": len(members),
            "mean_noul": (
                sum(float(record["noul"]) for record in members) / len(members)
                if members
                else None
            ),
            "max_noul": max((float(record["noul"]) for record in members), default=None),
            "false_positives_at_0_50": sum(
                float(record["noul"]) >= REFERENCE_THRESHOLD for record in members
            ),
        }
    errors_fixed = [
        {
            "id": record["id"],
            "split": record["split"],
            "language": record["language"],
            "change_type": record["change_type"],
            "expected": record["expected"],
            "noul": record["noul"],
        }
        for record in successful
        if (float(record["noul"]) >= REFERENCE_THRESHOLD) is not bool(record["expected"])
    ]
    errors_selected_validation = (
        [
            {
                "id": record["id"],
                "language": record["language"],
                "change_type": record["change_type"],
                "expected": record["expected"],
                "noul": record["noul"],
            }
            for record in validation
            if (float(record["noul"]) >= selected_threshold) is not bool(record["expected"])
        ]
        if selected_threshold is not None
        else []
    )
    return {
        "schema_version": 2,
        "kind": "paired_prompt_preservation_evaluation",
        "run_id": run_id,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "dataset": {
            "path": common.display_path(dataset_path),
            "sha256": common.dataset_sha256(dataset_path),
            "total_cases": 24,
            "requested_cases": requested_cases,
            "pairs": 12,
            "splits": {"calibration": 12, "validation": 12},
            "languages": {"en": 12, "zh": 12},
        },
        "protocol": {
            "mode": "Noul",
            "instructions": common.INSTRUCTIONS,
            "instructions_sha256": hashlib.sha256(common.INSTRUCTIONS.encode("utf-8")).hexdigest(),
            "reference_threshold": REFERENCE_THRESHOLD,
            "calibration_threshold_grid": list(THRESHOLD_GRID),
            "automatic_retries": 0,
        },
        "requested_model": model,
        "returned_models": dict(sorted(Counter(record["model"] for record in successful).items())),
        "request_attempts": attempts,
        "successful_responses": len(successful),
        "failed_responses": attempts - len(successful),
        "usage_totals": usage_totals(successful),
        "elapsed_ms_total": sum(int(record["elapsed_ms"]) for record in successful),
        "fixed_threshold_results": fixed,
        "calibration_grid": calibration_grid,
        "selected_threshold_results": selected,
        "language_results_at_0_50": language_results,
        "negative_type_results_at_0_50": negative_types,
        "pair_ranking": pair_results(successful),
        "errors_at_0_50": errors_fixed,
        "validation_errors_at_selected_threshold": errors_selected_validation,
        "stop_error": stop_error,
        "limitations": [
            "Twenty-four hand-authored paired cases are not a sample of real user traffic.",
            "Calibration and validation are separate, but both were authored under the same protocol.",
            "Only English and Chinese explicit prompt constraints in Noul mode are covered.",
            "One provider model version and one run do not establish temporal stability.",
        ],
    }


def fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def render_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    selected = summary["selected_threshold_results"]
    lines = [
        "# SJ18-v2 paired prompt-preservation result",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Status: `{summary['status']}`",
        f"- Dataset SHA-256: `{summary['dataset']['sha256']}`",
        f"- Requested model: `{summary['requested_model']}`",
        f"- Returned models: `{common.canonical_json(summary['returned_models'])}`",
        f"- Requests: {summary['request_attempts']} attempted, {summary['successful_responses']} successful, no automatic retries",
        "",
        "## Reference threshold 0.50",
        "",
        "| split | n | TP | TN | FP | FN | balanced | Brier | AUROC |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ("all", "calibration", "validation"):
        result = summary["fixed_threshold_results"][split]
        metric = result["metrics"]
        matrix = metric["confusion_matrix"]
        lines.append(
            f"| {split} | {metric['sample_count']} | {matrix['tp']} | {matrix['tn']} | {matrix['fp']} | {matrix['fn']} | "
            f"{fmt(metric['balanced_accuracy'])} | {fmt(result['brier_score'])} | {fmt(result['auroc'])} |"
        )
    lines.extend(["", "## Calibration-selected threshold", ""])
    if selected is None:
        lines.append("Threshold selection was unavailable because calibration did not complete.")
    else:
        lines.append(
            f"Calibration selected `{selected['threshold']:.2f}` using maximum balanced accuracy; ties prefer the value closest to 0.50, then the lower value."
        )
        lines.extend(
            [
                "",
                "| split | TP | TN | FP | FN | balanced | Brier | AUROC |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for split in ("calibration", "validation"):
            result = selected[split]
            metric = result["metrics"]
            matrix = metric["confusion_matrix"]
            lines.append(
                f"| {split} | {matrix['tp']} | {matrix['tn']} | {matrix['fp']} | {matrix['fn']} | "
                f"{fmt(metric['balanced_accuracy'])} | {fmt(result['brier_score'])} | {fmt(result['auroc'])} |"
            )

    lines.extend(
        [
            "",
            "## Calibration threshold grid",
            "",
            "| threshold | TP | TN | FP | FN | balanced | recall | specificity |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for metric in summary["calibration_grid"]:
        matrix = metric["confusion_matrix"]
        lines.append(
            f"| {metric['threshold']:.2f} | {matrix['tp']} | {matrix['tn']} | {matrix['fp']} | {matrix['fn']} | "
            f"{fmt(metric['balanced_accuracy'])} | {fmt(metric['recall'])} | {fmt(metric['specificity'])} |"
        )

    lines.extend(
        [
            "",
            "## Language results at 0.50",
            "",
            "| language | TP | TN | FP | FN | balanced | Brier | AUROC |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for language in LANGUAGES:
        result = summary["language_results_at_0_50"][language]
        metric = result["metrics"]
        matrix = metric["confusion_matrix"]
        lines.append(
            f"| {language} | {matrix['tp']} | {matrix['tn']} | {matrix['fp']} | {matrix['fn']} | "
            f"{fmt(metric['balanced_accuracy'])} | {fmt(result['brier_score'])} | {fmt(result['auroc'])} |"
        )

    lines.extend(
        [
            "",
            "## Negative change types at 0.50",
            "",
            "| change type | n | mean p(true) | max p(true) | false positives |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for change_type in NEGATIVE_TYPES:
        result = summary["negative_type_results_at_0_50"][change_type]
        lines.append(
            f"| {change_type} | {result['sample_count']} | {fmt(result['mean_noul'])} | "
            f"{fmt(result['max_noul'])} | {result['false_positives_at_0_50']} |"
        )

    ranking = summary["pair_ranking"]
    lines.extend(
        [
            "",
            "## Pair ranking",
            "",
            f"Correctly ranked: {ranking['correctly_ranked']}/{ranking['complete_pairs']}; mean margin `{fmt(ranking['mean_margin'])}`, minimum margin `{fmt(ranking['minimum_margin'])}`.",
            "",
            "| pair | split | language | positive p | negative p | margin | ranked |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for pair in ranking["pairs"]:
        lines.append(
            f"| {pair['pair_id']} | {pair['split']} | {pair['language']} | {pair['positive_noul']:.3f} | "
            f"{pair['negative_noul']:.3f} | {pair['margin']:.3f} | {str(pair['correctly_ranked']).lower()} |"
        )

    lines.extend(
        [
            "",
            "## Per-case probabilities",
            "",
            "| id | split | language | change | expected | p(true) | model | elapsed ms |",
            "| --- | --- | --- | --- | --- | ---: | --- | ---: |",
        ]
    )
    for record in records:
        probability = "error" if record.get("noul") is None else f"{record['noul']:.3f}"
        lines.append(
            f"| {record['id']} | {record['split']} | {record['language']} | {record['change_type']} | "
            f"{str(record['expected']).lower()} | {probability} | {record.get('model') or ''} | {record.get('elapsed_ms') or ''} |"
        )
    lines.extend(["", "## Errors at reference threshold 0.50", ""])
    if not summary["errors_at_0_50"]:
        lines.append("No errors.")
    else:
        for error in summary["errors_at_0_50"]:
            lines.append(
                f"- `{error['id']}` ({error['split']}, {error['language']}, {error['change_type']}): "
                f"expected `{str(error['expected']).lower()}`, p(true) `{error['noul']:.3f}`."
            )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- These are authored diagnostic pairs, not sampled production prompts.",
            "- Calibration and validation are separate but share the same authoring process.",
            "- Results cover one run of one returned provider model version.",
            "",
        ]
    )
    return "\n".join(lines)


async def run_real_evaluation(
    *,
    cases: list[dict[str, Any]],
    dataset_path: Path,
    model: str,
    max_requests: int,
    output_dir: Path,
    run_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    common.load_local_key()
    protocol, backend = common.load_plugin_modules()
    service = backend.DecisionService(backend.TypeSafeBackend(), capacity=max_requests)
    started_at = datetime.now().astimezone().isoformat()
    records: list[dict[str, Any]] = []
    stop_error: dict[str, str] | None = None
    attempts = 0
    selected_cases = cases[:max_requests]
    for case in selected_cases:
        attempts += 1
        try:
            request = protocol.DecisionRequest.create(
                context={"original": case["original"], "candidate": case["candidate"]},
                instructions=common.INSTRUCTIONS,
                mode="Noul",
                options_text="",
                threshold=REFERENCE_THRESHOLD,
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
                "pair_id": case["pair_id"],
                "split": case["split"],
                "language": case["language"],
                "change_type": case["change_type"],
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
            stop_error = common.safe_error(error)
            record = {
                "id": case["id"],
                "pair_id": case["pair_id"],
                "split": case["split"],
                "language": case["language"],
                "change_type": case["change_type"],
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
        common.write_text_atomic(
            output_dir / "cases.partial.jsonl",
            "".join(common.canonical_json(item) + "\n" for item in records),
        )
        if stop_error is not None:
            break

    status = (
        "stopped_on_error"
        if stop_error is not None
        else "limited_by_request_cap"
        if len(selected_cases) < len(cases)
        else "complete"
    )
    summary = build_summary(
        run_id=run_id,
        dataset_path=dataset_path,
        model=model,
        records=records,
        attempts=attempts,
        requested_cases=len(selected_cases),
        status=status,
        started_at=started_at,
        finished_at=datetime.now().astimezone().isoformat(),
        stop_error=stop_error,
    )
    common.write_json_atomic(output_dir / "summary.partial.json", summary)
    common.write_text_atomic(output_dir / "report.partial.md", render_report(summary, records))
    if status == "complete":
        (output_dir / "cases.partial.jsonl").replace(output_dir / "cases.jsonl")
        (output_dir / "summary.partial.json").replace(output_dir / "summary.json")
        (output_dir / "report.partial.md").replace(output_dir / "report.md")
    return summary, records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--max-requests", type=int, default=24)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        dataset_path = args.dataset.resolve()
        cases = load_dataset(dataset_path)
        if not 1 <= args.max_requests <= len(cases):
            raise ValueError(f"max-requests must be between 1 and {len(cases)}")
        if not isinstance(args.model, str) or not args.model.strip():
            raise ValueError("model must be nonempty")
        if args.dry_run:
            print(
                common.canonical_json(
                    {
                        "ok": True,
                        "dry_run": True,
                        "dataset": common.display_path(dataset_path),
                        "dataset_sha256": common.dataset_sha256(dataset_path),
                        "cases": len(cases),
                        "pairs": len({case["pair_id"] for case in cases}),
                        "splits": dict(sorted(Counter(case["split"] for case in cases).items())),
                        "languages": dict(sorted(Counter(case["language"] for case in cases).items())),
                        "class_counts": {
                            "positive": sum(case["expected"] for case in cases),
                            "negative": sum(not case["expected"] for case in cases),
                        },
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
            common.canonical_json(
                {
                    "ok": summary["status"] == "complete",
                    "status": summary["status"],
                    "run_id": run_id,
                    "output_dir": common.display_path(output_dir),
                    "request_attempts": summary["request_attempts"],
                    "successful_responses": summary["successful_responses"],
                    "returned_models": summary["returned_models"],
                }
            )
        )
        return 0 if summary["status"] == "complete" else 1
    except Exception as error:
        print(common.canonical_json({"ok": False, "error": common.safe_error(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
