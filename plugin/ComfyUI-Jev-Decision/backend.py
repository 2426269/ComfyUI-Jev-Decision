"""Backend abstraction and bounded response cache for Semantic Judge."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import time
from typing import Any, Protocol

from . import provider
from .decision_protocol import (
    DecisionRequest,
    build_question,
    canonical_dumps,
    strict_loads,
    validate_provider_response,
)


class DecisionBackend(Protocol):
    name: str

    async def evaluate(self, request: DecisionRequest) -> dict[str, Any]:
        ...


class TypeSafeBackend:
    name = "typesafe"

    async def evaluate(self, request: DecisionRequest) -> dict[str, Any]:
        return await provider.evaluate(
            request.context,
            {"decision": build_question(request)},
            request.model,
            request.connection_profile,
        )


@dataclass(frozen=True, slots=True)
class Evaluation:
    response: dict[str, Any]
    cache_hit: bool
    cache_key_sha256: str
    elapsed_ms: int


def cache_key_sha256(backend_name: str, request: DecisionRequest) -> str:
    material = {
        "backend": backend_name,
        "connection_profile": request.connection_profile,
        "model": request.model,
        "mode": request.mode,
        "context": request.context,
        "instructions": request.instructions,
        "options": request.options_document(),
        "refresh": request.refresh,
    }
    return hashlib.sha256(canonical_dumps(material).encode("utf-8")).hexdigest()


class DecisionService:
    def __init__(self, backend: DecisionBackend, capacity: int = 256):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("Cache capacity must be a positive integer")
        self.backend = backend
        self.capacity = capacity
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._inflight: dict[str, asyncio.Task[str]] = {}
        self._lock = asyncio.Lock()

    async def _fetch_and_cache(
        self,
        key: str,
        request: DecisionRequest,
    ) -> str:
        task = asyncio.current_task()
        try:
            raw_response = await self.backend.evaluate(request)
            validated = validate_provider_response(request, raw_response)
            encoded = canonical_dumps(validated)
            async with self._lock:
                self._cache[key] = encoded
                self._cache.move_to_end(key)
                while len(self._cache) > self.capacity:
                    self._cache.popitem(last=False)
            return encoded
        finally:
            async with self._lock:
                if self._inflight.get(key) is task:
                    self._inflight.pop(key, None)

    async def evaluate(self, request: DecisionRequest) -> Evaluation:
        started = time.perf_counter()
        key = cache_key_sha256(self.backend.name, request)

        async with self._lock:
            encoded = self._cache.get(key)
            if encoded is not None:
                self._cache.move_to_end(key)
                return Evaluation(
                    response=strict_loads(encoded, "Cached provider response"),
                    cache_hit=True,
                    cache_key_sha256=key,
                    elapsed_ms=round((time.perf_counter() - started) * 1000),
                )

            task = self._inflight.get(key)
            is_leader = task is None
            if task is None:
                task = asyncio.create_task(self._fetch_and_cache(key, request))
                self._inflight[key] = task

        encoded = await asyncio.shield(task)
        return Evaluation(
            response=strict_loads(encoded, "Provider response"),
            cache_hit=not is_leader,
            cache_key_sha256=key,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

