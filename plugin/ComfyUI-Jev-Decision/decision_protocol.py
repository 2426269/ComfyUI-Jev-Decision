"""Pure contracts for the single-node Semantic Judge."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any


DETAILS_SCHEMA_VERSION = 1
MODES = ("Noul", "Choice", "Score")
PROBABILITY_TOLERANCE = 1e-4
PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"JSON numbers must be finite: {value}")


def strict_loads(text: str, label: str = "JSON") -> Any:
    if not isinstance(text, str):
        raise ValueError(f"{label} must be text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (TypeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{label}: {error}") from None


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"JSON values must be serializable and finite: {error}") from None


def _clean_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value.strip()


ContextState = str | dict[str, Any] | list[Any]


def _normalize_json_value(value: Any, active_containers: set[int]) -> Any:
    value_type = type(value)
    if value is None or value_type in (bool, int, str):
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("Context JSON numbers must be finite")
        return value
    if value_type is list:
        identity = id(value)
        if identity in active_containers:
            raise ValueError("Context must not contain cyclic arrays or objects")
        active_containers.add(identity)
        try:
            return [
                _normalize_json_value(item, active_containers) for item in value
            ]
        finally:
            active_containers.remove(identity)
    if value_type is dict:
        identity = id(value)
        if identity in active_containers:
            raise ValueError("Context must not contain cyclic arrays or objects")
        active_containers.add(identity)
        try:
            normalized: dict[str, Any] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError("Context object keys must be strings")
                normalized[key] = _normalize_json_value(item, active_containers)
            return normalized
        finally:
            active_containers.remove(identity)
    raise ValueError(
        "Context must be STRING, DICT, ARRAY, BOOLEAN, INT, or FLOAT "
        "containing only JSON values"
    )


def normalize_context(value: Any) -> ContextState:
    value_type = type(value)
    if value_type is str:
        return _clean_text(value, "Context")
    if value_type in (bool, int, float):
        return {"value": _normalize_json_value(value, set())}
    if value_type in (dict, list):
        if not value:
            raise ValueError("Context object or array must be nonempty")
        return _normalize_json_value(value, set())
    raise ValueError(
        "Context must be STRING, DICT, ARRAY, BOOLEAN, INT, or FLOAT"
    )


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be a finite number")
    return converted


def _probability(value: Any, label: str) -> float:
    converted = _finite_number(value, label)
    if not 0.0 <= converted <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return converted


def _exact_fields(
    value: Any,
    required: set[str],
    optional: set[str],
    label: str,
    *,
    allow_unknown: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    fields = set(value)
    missing = required - fields
    unknown = fields - required - optional
    if missing:
        raise ValueError(f"{label} is missing fields: {sorted(missing)}")
    if unknown and not allow_unknown:
        raise ValueError(f"{label} has unknown fields: {sorted(unknown)}")
    return value


@dataclass(frozen=True, slots=True)
class DecisionOption:
    id: str
    description: str | None
    index: int

    def document(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "index": self.index,
        }


def parse_options(mode: str, options_text: str) -> tuple[DecisionOption, ...]:
    if mode not in MODES:
        raise ValueError(f"Mode must be one of {MODES}")
    if not isinstance(options_text, str):
        raise ValueError("Options must be text")
    lines = [line.strip() for line in options_text.splitlines() if line.strip()]
    if mode == "Noul":
        if lines:
            raise ValueError("Noul mode does not accept options")
        return ()

    options: list[DecisionOption] = []
    seen: set[str] = set()
    for line in lines:
        option_id, separator, description = line.partition("|")
        option_id = option_id.strip()
        if not option_id:
            raise ValueError("Option ID must be nonempty")
        if any(ord(character) < 32 or ord(character) == 127 for character in option_id):
            raise ValueError(f"Option ID {option_id!r} contains a control character")
        if option_id in seen:
            raise ValueError(f"Duplicate option ID: {option_id}")
        seen.add(option_id)
        cleaned_description = description.strip() if separator else ""
        options.append(
            DecisionOption(
                id=option_id,
                description=cleaned_description or None,
                index=len(options),
            )
        )

    minimum, maximum = (2, 255) if mode == "Choice" else (2, 10)
    if not minimum <= len(options) <= maximum:
        raise ValueError(f"{mode} requires between {minimum} and {maximum} options")
    return tuple(options)


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    context: ContextState
    instructions: str
    mode: str
    options: tuple[DecisionOption, ...]
    threshold: float
    model: str
    connection_profile: str
    refresh: int

    @classmethod
    def create(
        cls,
        *,
        context: Any,
        instructions: str,
        mode: str,
        options_text: str,
        threshold: float,
        model: str,
        connection_profile: str,
        refresh: int,
    ) -> "DecisionRequest":
        cleaned_context = normalize_context(context)
        cleaned_instructions = _clean_text(instructions, "Instructions")
        if mode not in MODES:
            raise ValueError(f"Mode must be one of {MODES}")
        converted_threshold = _probability(threshold, "Threshold")
        cleaned_model = _clean_text(model, "Model")
        cleaned_profile = _clean_text(connection_profile, "Connection profile")
        if not PROFILE_PATTERN.fullmatch(cleaned_profile):
            raise ValueError(
                "Connection profile may contain only letters, numbers, '_' and '-'"
            )
        if isinstance(refresh, bool) or not isinstance(refresh, int) or refresh < 0:
            raise ValueError("Refresh must be a nonnegative integer")
        return cls(
            context=cleaned_context,
            instructions=cleaned_instructions,
            mode=mode,
            options=parse_options(mode, options_text),
            threshold=converted_threshold,
            model=cleaned_model,
            connection_profile=cleaned_profile,
            refresh=refresh,
        )

    def options_document(self) -> list[dict[str, Any]]:
        return [option.document() for option in self.options]


def build_question(request: DecisionRequest) -> dict[str, Any]:
    kind = request.mode.lower()
    question: dict[str, Any] = {
        "type": kind,
        "instructions": request.instructions,
    }
    if request.mode == "Choice":
        question["criteria"] = {
            option.id: option.description for option in request.options
        }
    elif request.mode == "Score":
        question["criteria"] = [
            option.description if option.description is not None else option.id
            for option in request.options
        ]
    return question


def _validate_distribution(
    value: Any,
    expected_keys: set[str],
    label: str,
) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ValueError(f"{label} probability keys do not match the options")
    converted = {
        key: _probability(probability, f"{label} probability {key!r}")
        for key, probability in value.items()
    }
    if abs(sum(converted.values()) - 1.0) > PROBABILITY_TOLERANCE:
        raise ValueError(f"{label} probabilities must sum to 1")
    return converted


def validate_provider_response(
    request: DecisionRequest,
    response: Any,
) -> dict[str, Any]:
    document = _exact_fields(
        response,
        {"model", "answers"},
        {"usage"},
        "Provider response",
        allow_unknown=True,
    )
    model = _clean_text(document["model"], "Provider response model")
    answers = _exact_fields(
        document["answers"],
        {"decision"},
        set(),
        "Provider response answers",
        allow_unknown=True,
    )
    answer = answers["decision"]
    expected_type = request.mode.lower()

    if expected_type == "noul":
        checked = _exact_fields(
            answer,
            {"type", "noul"},
            set(),
            "Noul answer",
            allow_unknown=True,
        )
        if checked["type"] != "noul":
            raise ValueError("Noul answer has the wrong type")
        _probability(checked["noul"], "Noul probability")
    elif expected_type == "choice":
        checked = _exact_fields(
            answer,
            {"type", "choice", "probabilities", "confidence"},
            set(),
            "Choice answer",
            allow_unknown=True,
        )
        if checked["type"] != "choice":
            raise ValueError("Choice answer has the wrong type")
        option_ids = {option.id for option in request.options}
        if checked["choice"] not in option_ids:
            raise ValueError("Choice answer selected an unknown option")
        _validate_distribution(checked["probabilities"], option_ids, "Choice answer")
        _probability(checked["confidence"], "Choice confidence")
    else:
        checked = _exact_fields(
            answer,
            {"type", "score", "legend", "probabilities", "confidence"},
            set(),
            "Score answer",
            allow_unknown=True,
        )
        if checked["type"] != "score":
            raise ValueError("Score answer has the wrong type")
        level_keys = {str(index) for index in range(len(request.options))}
        probabilities = _validate_distribution(
            checked["probabilities"],
            level_keys,
            "Score answer",
        )
        expected_legend = {
            str(option.index): (
                option.description if option.description is not None else option.id
            )
            for option in request.options
        }
        if checked["legend"] != expected_legend:
            raise ValueError("Score legend does not match the supplied levels")
        score = _finite_number(checked["score"], "Score")
        if not 0.0 <= score <= len(request.options) - 1:
            raise ValueError("Score is outside the supplied levels")
        expected_score = sum(
            int(level) * probability for level, probability in probabilities.items()
        )
        if abs(score - expected_score) > PROBABILITY_TOLERANCE:
            raise ValueError("Score does not match its probability distribution")
        _probability(checked["confidence"], "Score confidence")

    usage = document.get("usage")
    if usage is not None and not isinstance(usage, dict):
        raise ValueError("Provider usage must be an object when present")

    normalized = {
        "model": model,
        "answers": {"decision": checked},
        "usage": usage,
    }
    return strict_loads(canonical_dumps(normalized), "Validated provider response")


@dataclass(frozen=True, slots=True)
class SemanticOutputs:
    boolean: bool
    float_value: float
    int_value: int
    string_value: str
    details_json: str

    def values(self) -> tuple[bool, float, int, str]:
        return (
            self.boolean,
            self.float_value,
            self.int_value,
            self.string_value,
        )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def context_sha256(value: ContextState) -> str:
    if isinstance(value, str):
        return _sha256_text(value)
    kind = "object" if isinstance(value, dict) else "array"
    material = f"{kind}:{canonical_dumps(value)}"
    return _sha256_text(material)


def map_outputs(
    request: DecisionRequest,
    response: dict[str, Any],
    *,
    backend: str,
    elapsed_ms: int,
    cache_hit: bool,
    cache_key_sha256: str,
) -> SemanticOutputs:
    validated = validate_provider_response(request, response)
    answer = validated["answers"]["decision"]

    if request.mode == "Noul":
        float_value = float(answer["noul"])
        boolean = float_value >= request.threshold
        int_value = int(boolean)
        string_value = "true" if boolean else "false"
    elif request.mode == "Choice":
        float_value = float(answer["confidence"])
        boolean = float_value >= request.threshold
        string_value = answer["choice"]
        int_value = next(
            option.index for option in request.options if option.id == string_value
        )
    else:
        raw_score = float(answer["score"])
        float_value = raw_score / (len(request.options) - 1)
        boolean = float_value >= request.threshold
        int_value = min(
            max(math.floor(raw_score + 0.5), 0),
            len(request.options) - 1,
        )
        string_value = request.options[int_value].id

    outputs_document = {
        "boolean": boolean,
        "float": float_value,
        "int": int_value,
        "string": string_value,
    }
    options_json = canonical_dumps(request.options_document())
    details = {
        "schema_version": DETAILS_SCHEMA_VERSION,
        "kind": "semantic_judge_result",
        "backend": _clean_text(backend, "Backend"),
        "requested_model": request.model,
        "model": validated["model"],
        "mode": request.mode.lower(),
        "input_fingerprints": {
            "context_sha256": context_sha256(request.context),
            "instructions_sha256": _sha256_text(request.instructions),
            "options_sha256": _sha256_text(options_json),
        },
        "options": request.options_document(),
        "threshold": request.threshold,
        "outputs": outputs_document,
        "answer": answer,
        "usage": validated["usage"],
        "elapsed_ms": elapsed_ms,
        "cache": {
            "hit": bool(cache_hit),
            "key_sha256": cache_key_sha256,
        },
    }
    return SemanticOutputs(
        boolean=boolean,
        float_value=float_value,
        int_value=int_value,
        string_value=string_value,
        details_json=canonical_dumps(details),
    )
