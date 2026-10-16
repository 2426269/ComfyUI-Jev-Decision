import asyncio
import importlib
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "jev_decision_backend_tests"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE_NAME] = package

protocol = importlib.import_module(f"{PACKAGE_NAME}.decision_protocol")
provider = importlib.import_module(f"{PACKAGE_NAME}.provider")


def request(
    context="state",
    *,
    instructions="Is this true?",
    mode="Noul",
    options="",
    threshold=0.5,
    model="jev-latest",
    refresh=0,
    profile="default",
):
    return protocol.DecisionRequest.create(
        context=context,
        instructions=instructions,
        mode=mode,
        options_text=options,
        threshold=threshold,
        model=model,
        connection_profile=profile,
        refresh=refresh,
    )


def noul_response(value=0.8):
    return {
        "model": "jev-test",
        "answers": {"decision": {"type": "noul", "noul": value}},
        "usage": {"input_tokens": 4, "output_tokens": 1},
    }


class ProviderProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_profile_uses_default_environment_variable(self):
        response = noul_response()
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "secret"}, clear=True):
            with patch.object(provider, "_post_json", AsyncMock(return_value=response)) as post:
                result = await provider.evaluate(
                    "state",
                    {"decision": {"type": "noul", "instructions": "Is this true?"}},
                    "jev-latest",
                    "default",
                )
        self.assertEqual(result, response)
        endpoint, payload, api_key = post.await_args.args
        self.assertEqual(endpoint, provider.TYPESAFE_ENDPOINT)
        self.assertEqual(api_key, "secret")
        self.assertEqual(payload["model"], "jev-latest")
        self.assertEqual(payload["state"], "state")
        self.assertIn("decision", payload["questions"])

    async def test_named_profile_maps_to_scoped_environment_variable(self):
        with patch.dict(
            os.environ,
            {"TYPESAFE_API_KEY_WORK_STATION": "named-secret"},
            clear=True,
        ):
            with patch.object(provider, "_post_json", AsyncMock(return_value={})) as post:
                await provider.evaluate({}, {}, "jev-1.13.0", "work-station")
        self.assertEqual(post.await_args.args[2], "named-secret")

    async def test_missing_key_reports_variable_name_without_a_secret(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TYPESAFE_API_KEY_TEST"):
                await provider.evaluate("state", {}, "jev-latest", "test")


class FakeResponse:
    def __init__(self, status, body="{}"):
        self.status = status
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def text(self):
        return self.body

    async def read(self):
        return self.body.encode()


class RaisingContext:
    def __init__(self, error):
        self.error = error

    async def __aenter__(self):
        raise self.error

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession:
    def __init__(self, response=None, enter_error=None):
        self.response = response
        self.enter_error = enter_error
        self.post_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def post(self, *args, **kwargs):
        self.post_kwargs = kwargs
        if self.enter_error is not None:
            return RaisingContext(self.enter_error)
        return self.response


class HttpBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_documented_http_statuses_have_specific_classification(self):
        expected_fragments = {
            400: "rejected",
            401: "authentication",
            402: "credits",
            403: "permitted",
            404: "not found",
            422: "rejected",
            429: "rate limit",
            529: "overloaded",
        }
        for status, fragment in expected_fragments.items():
            with self.subTest(status=status):
                self.assertIn(fragment, provider._error_for_status(status))
        self.assertEqual(provider.REQUEST_TIMEOUT_SECONDS, 60)

    async def test_http_error_is_classified_and_does_not_leak_key(self):
        session = FakeSession(FakeResponse(401, '{"message":"bad"}'))
        with patch.object(provider.aiohttp, "ClientSession", return_value=session):
            with self.assertRaises(RuntimeError) as raised:
                await provider._post_json("https://example.invalid", {}, "super-secret")
        self.assertIn("authentication failed", str(raised.exception))
        self.assertNotIn("super-secret", str(raised.exception))
        self.assertFalse(session.post_kwargs["allow_redirects"])

    async def test_timeout_is_reported_without_retry(self):
        session = FakeSession(enter_error=asyncio.TimeoutError())
        with patch.object(provider.aiohttp, "ClientSession", return_value=session):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                await provider._post_json("https://example.invalid", {}, "secret")

    async def test_non_object_json_is_rejected(self):
        session = FakeSession(FakeResponse(200, "[]"))
        with patch.object(provider.aiohttp, "ClientSession", return_value=session):
            with self.assertRaisesRegex(ValueError, "JSON object"):
                await provider._post_json("https://example.invalid", {}, "secret")


class FakeBackend:
    name = "fake"

    def __init__(self, *, delay=0):
        self.calls = 0
        self.delay = delay
        self.fail = False

    async def evaluate(self, decision_request):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("planned failure")
        return noul_response()


class DecisionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend_module = importlib.import_module(f"{PACKAGE_NAME}.backend")

    async def test_threshold_reuses_validated_response_but_refresh_does_not(self):
        fake = FakeBackend()
        service = self.backend_module.DecisionService(fake, capacity=8)

        first = await service.evaluate(request(threshold=0.5))
        threshold_only = await service.evaluate(request(threshold=0.9))
        refreshed = await service.evaluate(request(threshold=0.9, refresh=1))

        self.assertEqual(fake.calls, 2)
        self.assertFalse(first.cache_hit)
        self.assertTrue(threshold_only.cache_hit)
        self.assertFalse(refreshed.cache_hit)
        self.assertEqual(first.cache_key_sha256, threshold_only.cache_key_sha256)

    async def test_profile_is_part_of_the_cache_key(self):
        fake = FakeBackend()
        service = self.backend_module.DecisionService(fake, capacity=8)
        await service.evaluate(request(profile="default"))
        await service.evaluate(request(profile="work"))
        self.assertEqual(fake.calls, 2)

    async def test_every_semantic_input_changes_the_cache_key(self):
        fake = FakeBackend()
        service = self.backend_module.DecisionService(fake, capacity=16)
        requests = [
            request(),
            request(context="other state"),
            request(instructions="A different question?"),
            request(
                mode="Choice",
                options="yes | affirmative\nno | negative",
            ),
            request(
                mode="Choice",
                options="yes | positive\nno | negative",
            ),
            request(model="jev-pinned"),
            request(profile="work"),
            request(refresh=1),
        ]
        for decision_request in requests:
            if decision_request.mode == "Choice":
                fake_response = {
                    "model": "jev-test",
                    "answers": {
                        "decision": {
                            "type": "choice",
                            "choice": "yes",
                            "probabilities": {"yes": 0.8, "no": 0.2},
                            "confidence": 0.8,
                        }
                    },
                }
                with patch.object(fake, "evaluate", AsyncMock(return_value=fake_response)):
                    await service.evaluate(decision_request)
                fake.calls += 1
            else:
                await service.evaluate(decision_request)
        self.assertEqual(fake.calls, len(requests))

    async def test_errors_are_not_cached(self):
        fake = FakeBackend()
        fake.fail = True
        service = self.backend_module.DecisionService(fake, capacity=8)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, "planned failure"):
                await service.evaluate(request())
        self.assertEqual(fake.calls, 2)

    async def test_lru_evicts_oldest_entry(self):
        fake = FakeBackend()
        service = self.backend_module.DecisionService(fake, capacity=2)
        await service.evaluate(request("a"))
        await service.evaluate(request("b"))
        await service.evaluate(request("c"))
        await service.evaluate(request("a"))
        self.assertEqual(fake.calls, 4)

    async def test_concurrent_identical_requests_are_coalesced(self):
        fake = FakeBackend(delay=0.02)
        service = self.backend_module.DecisionService(fake, capacity=8)
        first, second = await asyncio.gather(
            service.evaluate(request()),
            service.evaluate(request()),
        )
        self.assertEqual(fake.calls, 1)
        self.assertEqual({first.cache_hit, second.cache_hit}, {False, True})

    async def test_typesafe_backend_builds_one_decision_question(self):
        backend = self.backend_module.TypeSafeBackend()
        with patch.object(
            provider,
            "evaluate",
            AsyncMock(return_value=noul_response()),
        ) as evaluate:
            response = await backend.evaluate(request())
        self.assertEqual(response["model"], "jev-test")
        evaluate.assert_awaited_once_with(
            "state",
            {
                "decision": {
                    "type": "noul",
                    "instructions": "Is this true?",
                }
            },
            "jev-latest",
            "default",
        )

    async def test_typesafe_backend_preserves_structured_state(self):
        backend = self.backend_module.TypeSafeBackend()
        structured = {"prompt": "雨夜", "facts": ["two adults", False, 0]}
        with patch.object(
            provider,
            "evaluate",
            AsyncMock(return_value=noul_response()),
        ) as evaluate:
            await backend.evaluate(request(context=structured))
        self.assertEqual(evaluate.await_args.args[0], structured)

    async def test_cache_distinguishes_text_from_structured_context(self):
        fake = FakeBackend()
        service = self.backend_module.DecisionService(fake, capacity=8)
        await service.evaluate(request(context='{"a":1}'))
        await service.evaluate(request(context={"a": 1}))
        await service.evaluate(request(context={"a": 1}))
        self.assertEqual(fake.calls, 2)

    async def test_typesafe_backend_builds_choice_and_score_questions(self):
        backend = self.backend_module.TypeSafeBackend()
        cases = [
            (
                request(mode="Choice", options="portrait | 人像\nscene | 场景"),
                {
                    "type": "choice",
                    "instructions": "Is this true?",
                    "criteria": {"portrait": "人像", "scene": "场景"},
                },
            ),
            (
                request(mode="Score", options="low | 低\nhigh | 高"),
                {
                    "type": "score",
                    "instructions": "Is this true?",
                    "criteria": ["低", "高"],
                },
            ),
        ]
        for decision_request, expected_question in cases:
            with self.subTest(mode=decision_request.mode):
                with patch.object(
                    provider,
                    "evaluate",
                    AsyncMock(return_value={}),
                ) as evaluate:
                    await backend.evaluate(decision_request)
                self.assertEqual(
                    evaluate.await_args.args[1],
                    {"decision": expected_question},
                )


if __name__ == "__main__":
    unittest.main()
