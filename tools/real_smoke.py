"""Run exactly one credential-safe Semantic Judge Noul smoke request."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugin" / "ComfyUI-Jev-Decision"
ENV_FILE = ROOT / "local-runtime" / ".env.local"
PACKAGE_NAME = "jev_decision_real_smoke"


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


def load_plugin_modules():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PLUGIN_ROOT)]
    sys.modules[PACKAGE_NAME] = package
    protocol = importlib.import_module(f"{PACKAGE_NAME}.decision_protocol")
    backend = importlib.import_module(f"{PACKAGE_NAME}.backend")
    return protocol, backend


async def main() -> None:
    load_local_key()
    protocol, backend = load_plugin_modules()

    state = {
        "original": (
            "Two adult women stand together on a rainy city street at night, "
            "anime style, wide shot, no umbrellas."
        ),
        "candidate": (
            "Wide anime-style night view of two adult women together on a rain-soaked "
            "city street, without umbrellas; wet pavement adds reflected neon light."
        ),
    }
    request = protocol.DecisionRequest.create(
        context=protocol.canonical_dumps(state),
        instructions=(
            "Does candidate preserve every concrete requirement and prohibition in original "
            "without changing their meaning? Added compatible detail is allowed."
        ),
        mode="Noul",
        options_text="",
        threshold=0.5,
        model="jev-latest",
        connection_profile="default",
        refresh=0,
    )

    service = backend.DecisionService(backend.TypeSafeBackend(), capacity=1)
    evaluation = await service.evaluate(request)
    outputs = protocol.map_outputs(
        request,
        evaluation.response,
        backend=service.backend.name,
        elapsed_ms=evaluation.elapsed_ms,
        cache_hit=evaluation.cache_hit,
        cache_key_sha256=evaluation.cache_key_sha256,
    )
    details = protocol.strict_loads(outputs.details_json, "Smoke details")
    usage = details.get("usage")
    if usage is not None and not isinstance(usage, dict):
        usage = {"reported_type": type(usage).__name__}

    summary = {
        "ok": True,
        "request_count": 1,
        "model": details["model"],
        "mode": "noul",
        "noul": outputs.float_value,
        "threshold_0_5": outputs.boolean,
        "usage": usage,
        "elapsed_ms": details["elapsed_ms"],
        "response_fields": sorted(evaluation.response),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None
