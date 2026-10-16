"""Run one credential-safe Choice request and one Score request without retries."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugin" / "ComfyUI-Jev-Decision"
ENV_FILE = ROOT / "local-runtime" / ".env.local"
DEFAULT_OUTPUT = ROOT / "records" / "choice-score-smoke-20260922.json"
PACKAGE_NAME = "jev_decision_choice_score_smoke"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


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


def safe_error(error: Exception) -> dict[str, str]:
    message = str(error)
    key = os.environ.get("TYPESAFE_API_KEY", "")
    if key:
        message = message.replace(key, "[redacted]")
    if len(message) > 300:
        message = message[:297] + "..."
    return {"type": type(error).__name__, "message": message}


def load_plugin_modules() -> tuple[Any, Any]:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PLUGIN_ROOT)]
    sys.modules[PACKAGE_NAME] = package
    protocol = importlib.import_module(f"{PACKAGE_NAME}.decision_protocol")
    backend = importlib.import_module(f"{PACKAGE_NAME}.backend")
    return protocol, backend


def build_requests(protocol: Any, model: str) -> list[Any]:
    return [
        protocol.DecisionRequest.create(
            context={
                "prompt": "close-up studio portrait of one woman, neutral backdrop",
                "available_profiles": ["portrait", "environment"],
            },
            instructions="Choose the profile that best matches the prompt emphasis.",
            mode="Choice",
            options_text=(
                "portrait | subject-centered portrait composition\n"
                "environment | scene-centered environmental composition"
            ),
            threshold=0.5,
            model=model,
            connection_profile="default",
            refresh=0,
        ),
        protocol.DecisionRequest.create(
            context={
                "prompt": (
                    "three dancers crossing paths with overlapping arms and flowing fabric"
                )
            },
            instructions="Score the visual interaction complexity of the prompt.",
            mode="Score",
            options_text=(
                "simple | one static subject with little overlap\n"
                "moderate | multiple elements with some interaction\n"
                "complex | strong overlap, motion, or multi-subject interaction"
            ),
            threshold=0.5,
            model=model,
            connection_profile="default",
            refresh=0,
        ),
    ]


def inspect_raw_response(request: Any, response: Any, protocol: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {
            "response_type": type(response).__name__,
            "response_sha256": hashlib.sha256(
                canonical_json(response).encode("utf-8")
            ).hexdigest(),
        }
    answers = response.get("answers")
    answer = answers.get("decision") if isinstance(answers, dict) else None
    expected_answer_fields = (
        {"type", "choice", "probabilities", "confidence"}
        if request.mode == "Choice"
        else {"type", "score", "legend", "probabilities", "confidence"}
    )
    known_answer = {}
    if isinstance(answer, dict):
        known_answer = {
            key: answer[key]
            for key in sorted(expected_answer_fields)
            if key in answer
        }
    return {
        "response_type": "object",
        "response_sha256": hashlib.sha256(
            canonical_json(response).encode("utf-8")
        ).hexdigest(),
        "top_level_fields": sorted(response),
        "unknown_top_level_fields": sorted(set(response) - {"model", "answers", "usage"}),
        "answers_fields": sorted(answers) if isinstance(answers, dict) else None,
        "unknown_answers_fields": (
            sorted(set(answers) - {"decision"}) if isinstance(answers, dict) else None
        ),
        "answer_fields": sorted(answer) if isinstance(answer, dict) else None,
        "unknown_answer_fields": (
            sorted(set(answer) - expected_answer_fields)
            if isinstance(answer, dict)
            else None
        ),
        "known_answer": known_answer,
        "returned_model": response.get("model"),
        "usage": response.get("usage"),
    }


async def run(*, model: str, output: Path, dry_run: bool) -> int:
    protocol, backend_module = load_plugin_modules()
    requests = build_requests(protocol, model)
    if dry_run:
        print(
            canonical_json(
                {
                    "ok": True,
                    "dry_run": True,
                    "modes": [request.mode for request in requests],
                    "requests_sent": 0,
                }
            )
        )
        return 0
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    load_local_key()
    backend = backend_module.TypeSafeBackend()
    document: dict[str, Any] = {
        "schema_version": 1,
        "kind": "choice_score_real_smoke",
        "started_at": datetime.now().astimezone().isoformat(),
        "requested_model": model,
        "automatic_retries": 0,
        "results": [],
    }
    provider_failure = False
    for request in requests:
        started = time.perf_counter()
        try:
            raw_response = await backend.evaluate(request)
        except Exception as error:
            document["results"].append(
                {
                    "mode": request.mode,
                    "provider_ok": False,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                    "error": safe_error(error),
                }
            )
            provider_failure = True
            write_json_atomic(output, document)
            break

        result = {
            "mode": request.mode,
            "provider_ok": True,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "raw_contract": inspect_raw_response(request, raw_response, protocol),
            "strict_validation": None,
            "mapped_outputs": None,
        }
        try:
            validated = protocol.validate_provider_response(request, raw_response)
            outputs = protocol.map_outputs(
                request,
                validated,
                backend=backend.name,
                elapsed_ms=result["elapsed_ms"],
                cache_hit=False,
                cache_key_sha256=backend_module.cache_key_sha256(backend.name, request),
            )
            result["strict_validation"] = {"ok": True}
            result["mapped_outputs"] = {
                "boolean": outputs.boolean,
                "float": outputs.float_value,
                "int": outputs.int_value,
                "string": outputs.string_value,
            }
        except Exception as error:
            result["strict_validation"] = {
                "ok": False,
                "error": safe_error(error),
            }
        document["results"].append(result)
        write_json_atomic(output, document)

    document["finished_at"] = datetime.now().astimezone().isoformat()
    document["request_attempts"] = len(document["results"])
    document["complete"] = (
        len(document["results"]) == 2
        and all(result.get("provider_ok") for result in document["results"])
    )
    write_json_atomic(output, document)
    print(
        canonical_json(
            {
                "ok": document["complete"],
                "output": output.relative_to(ROOT).as_posix(),
                "request_attempts": document["request_attempts"],
                "modes": [result["mode"] for result in document["results"]],
                "strict_validation": {
                    result["mode"]: result.get("strict_validation")
                    for result in document["results"]
                },
            }
        )
    )
    return 1 if provider_failure or not document["complete"] else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(
            run(
                model=args.model.strip(),
                output=args.output.resolve(),
                dry_run=args.dry_run,
            )
        )
    except Exception as error:
        print(canonical_json({"ok": False, "error": safe_error(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
