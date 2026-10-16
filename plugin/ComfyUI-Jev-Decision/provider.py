"""TypeSafe provider boundary. This module contains the only outbound request path."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

import aiohttp

from .decision_protocol import strict_loads


TYPESAFE_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
REQUEST_TIMEOUT_SECONDS = 60
PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def profile_environment_name(connection_profile: str) -> str:
    if not isinstance(connection_profile, str) or not connection_profile.strip():
        raise ValueError("Connection profile must be nonempty text")
    profile = connection_profile.strip()
    if profile == "default":
        return "TYPESAFE_API_KEY"
    if not PROFILE_PATTERN.fullmatch(profile):
        raise ValueError("Connection profile may contain only letters, numbers, '_' and '-'")
    suffix = profile.upper().replace("-", "_")
    return f"TYPESAFE_API_KEY_{suffix}"


def _error_for_status(status: int) -> str:
    messages = {
        400: "request was rejected; check the state, questions, and model",
        401: "authentication failed",
        402: "account has insufficient credits",
        403: "request is not permitted",
        404: "endpoint or model was not found",
        422: "request inputs were rejected",
        429: "rate limit was exceeded",
        529: "provider is temporarily overloaded",
    }
    return messages.get(status, "request failed")


async def _post_json(endpoint: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    await response.read()
                    raise RuntimeError(
                        f"TypeSafe HTTP {response.status}: {_error_for_status(response.status)}"
                    )
                parsed = strict_loads(await response.text(), "TypeSafe response")
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"TypeSafe request timed out after {REQUEST_TIMEOUT_SECONDS} seconds"
        ) from None
    except aiohttp.ClientError as error:
        raise RuntimeError(
            f"TypeSafe connection failed ({type(error).__name__})"
        ) from None
    if not isinstance(parsed, dict):
        raise ValueError("TypeSafe response must be a JSON object")
    return parsed


async def evaluate(
    state: str | dict[str, Any] | list[Any],
    questions: dict[str, Any],
    model: str,
    connection_profile: str = "default",
) -> dict[str, Any]:
    if not isinstance(state, (str, dict, list)):
        raise ValueError("State must be text, an object, or an array")
    if not isinstance(questions, dict):
        raise ValueError("Questions must be an object")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model ID must be nonempty text")
    environment_name = profile_environment_name(connection_profile)
    api_key = os.environ.get(environment_name, "").strip()
    if not api_key:
        raise ValueError(
            f"Set {environment_name} in the environment that starts ComfyUI, then restart ComfyUI"
        )
    payload = {
        "model": model.strip(),
        "state": state,
        "questions": questions,
    }
    return await _post_json(TYPESAFE_ENDPOINT, payload, api_key)
