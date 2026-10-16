import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from decision_protocol import (
    DecisionRequest,
    build_question,
    context_sha256,
    map_outputs,
    parse_options,
    strict_loads,
    validate_provider_response,
)


class OptionParserTests(unittest.TestCase):
    def test_choice_options_preserve_order_unicode_and_first_separator(self):
        options = parse_options(
            "Choice",
            "portrait | 人像近景\n\nscene | 背景 | 大场景\nhosiery",
        )
        self.assertEqual(
            [(item.id, item.description, item.index) for item in options],
            [
                ("portrait", "人像近景", 0),
                ("scene", "背景 | 大场景", 1),
                ("hosiery", None, 2),
            ],
        )

    def test_option_ids_must_be_unique_nonempty_and_without_controls(self):
        bad_values = [
            "a | first\na | second",
            " | description\nb | valid",
            "a\u0007 | bad\nb | valid",
        ]
        for value in bad_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_options("Choice", value)

    def test_mode_specific_option_counts(self):
        self.assertEqual(parse_options("Noul", ""), ())
        with self.assertRaises(ValueError):
            parse_options("Noul", "yes")
        with self.assertRaises(ValueError):
            parse_options("Choice", "only")
        with self.assertRaises(ValueError):
            parse_options("Score", "low")
        with self.assertRaises(ValueError):
            parse_options("Score", "\n".join(f"l{i}" for i in range(11)))


class RequestTests(unittest.TestCase):
    def test_request_validation_and_question_building(self):
        request = DecisionRequest.create(
            context="  rainy portrait  ",
            instructions=" Which route fits? ",
            mode="Choice",
            options_text="portrait | 人像\nscene | 场景",
            threshold=0.8,
            model="jev-latest",
            connection_profile="default",
            refresh=0,
        )
        self.assertEqual(request.context, "rainy portrait")
        self.assertEqual(
            build_question(request),
            {
                "type": "choice",
                "instructions": "Which route fits?",
                "criteria": {"portrait": "人像", "scene": "场景"},
            },
        )

    def test_invalid_base_inputs_fail_before_a_request(self):
        cases = [
            {"context": "", "instructions": "x", "mode": "Noul", "threshold": 0.5},
            {"context": "x", "instructions": "", "mode": "Noul", "threshold": 0.5},
            {"context": "x", "instructions": "x", "mode": "Other", "threshold": 0.5},
            {"context": "x", "instructions": "x", "mode": "Noul", "threshold": -0.1},
            {"context": "x", "instructions": "x", "mode": "Noul", "threshold": 1.1},
            {"context": "x", "instructions": "x", "mode": "Noul", "threshold": math.nan},
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    DecisionRequest.create(
                        options_text="",
                        model="jev-latest",
                        connection_profile="default",
                        refresh=0,
                        **case,
                    )

    def test_context_accepts_json_states_and_wraps_scalars(self):
        cases = [
            ({"prompt": "雨夜", "constraints": ["two adults", None]}, {"prompt": "雨夜", "constraints": ["two adults", None]}),
            (["portrait", {"weight": 0.75}], ["portrait", {"weight": 0.75}]),
            (False, {"value": False}),
            (0, {"value": 0}),
            (1.25, {"value": 1.25}),
        ]
        for supplied, expected in cases:
            with self.subTest(supplied=supplied):
                request = DecisionRequest.create(
                    context=supplied,
                    instructions="judge",
                    mode="Noul",
                    options_text="",
                    threshold=0.5,
                    model="jev-latest",
                    connection_profile="default",
                    refresh=0,
                )
                self.assertEqual(request.context, expected)
                if isinstance(supplied, (dict, list)):
                    self.assertIsNot(request.context, supplied)

    def test_context_rejects_empty_non_json_and_cyclic_values(self):
        cyclic = []
        cyclic.append(cyclic)
        invalid = [
            None,
            {},
            [],
            math.nan,
            math.inf,
            ("tuple",),
            object(),
            {1: "non-string key"},
            {"bad": math.nan},
            cyclic,
        ]
        for index, supplied in enumerate(invalid):
            with self.subTest(index=index, kind=type(supplied).__name__):
                with self.assertRaises(ValueError):
                    DecisionRequest.create(
                        context=supplied,
                        instructions="judge",
                        mode="Noul",
                        options_text="",
                        threshold=0.5,
                        model="jev-latest",
                        connection_profile="default",
                        refresh=0,
                    )

    def test_context_fingerprint_preserves_string_compatibility_and_type(self):
        self.assertEqual(
            context_sha256("state"),
            "4ba69735ca53765ed6a709edb56c6ea236b7193a3b29a6b390c346f0f4340e4e",
        )
        self.assertNotEqual(context_sha256('{"a":1}'), context_sha256({"a": 1}))
        self.assertEqual(context_sha256({"b": 2, "a": 1}), context_sha256({"a": 1, "b": 2}))


class OutputMappingTests(unittest.TestCase):
    def request(self, mode, options="", threshold=0.5):
        return DecisionRequest.create(
            context="state",
            instructions="judge",
            mode=mode,
            options_text=options,
            threshold=threshold,
            model="jev-latest",
            connection_profile="default",
            refresh=0,
        )

    def map(self, request, response, *, hit=False):
        validated = validate_provider_response(request, response)
        return map_outputs(
            request,
            validated,
            backend="typesafe",
            elapsed_ms=12,
            cache_hit=hit,
            cache_key_sha256="a" * 64,
        )

    def test_noul_boundary_mapping(self):
        request = self.request("Noul", threshold=0.7)
        outputs = self.map(
            request,
            {
                "model": "jev-1.13.0",
                "answers": {"decision": {"type": "noul", "noul": 0.7}},
                "usage": {"input_tokens": 10, "output_tokens": 2},
            },
        )
        self.assertEqual(outputs.values(), (True, 0.7, 1, "true"))
        details = json.loads(outputs.details_json)
        self.assertEqual(details["answer"]["noul"], 0.7)
        self.assertEqual(details["outputs"]["boolean"], True)
        self.assertNotIn('"context":', outputs.details_json)
        self.assertNotIn('"instructions":', outputs.details_json)

    def test_noul_zero_and_one_boundaries(self):
        request = self.request("Noul", threshold=1.0)
        for probability, expected in ((0.0, False), (1.0, True)):
            with self.subTest(probability=probability):
                outputs = self.map(
                    request,
                    {
                        "model": "jev-test",
                        "answers": {
                            "decision": {"type": "noul", "noul": probability}
                        },
                    },
                )
                self.assertEqual(outputs.boolean, expected)
                self.assertEqual(outputs.float_value, probability)

    def test_structured_context_details_store_only_a_typed_fingerprint(self):
        request = DecisionRequest.create(
            context={"private_prompt": "do not persist this phrase"},
            instructions="judge",
            mode="Noul",
            options_text="",
            threshold=0.5,
            model="jev-latest",
            connection_profile="default",
            refresh=0,
        )
        outputs = self.map(
            request,
            {"model": "jev-test", "answers": {"decision": {"type": "noul", "noul": 0.8}}},
        )
        details = json.loads(outputs.details_json)
        self.assertEqual(
            details["input_fingerprints"]["context_sha256"],
            context_sha256(request.context),
        )
        self.assertNotIn("private_prompt", outputs.details_json)
        self.assertNotIn("do not persist this phrase", outputs.details_json)

    def test_choice_uses_confidence_and_declared_index(self):
        request = self.request(
            "Choice",
            "portrait | close subject\nscene | large environment",
            threshold=0.8,
        )
        outputs = self.map(
            request,
            {
                "model": "jev-1.13.0",
                "answers": {
                    "decision": {
                        "type": "choice",
                        "choice": "scene",
                        "probabilities": {"portrait": 0.15, "scene": 0.85},
                        "confidence": 0.81,
                    }
                },
            },
        )
        self.assertEqual(outputs.values(), (True, 0.81, 1, "scene"))
        details = json.loads(outputs.details_json)
        self.assertEqual(details["answer"]["probabilities"]["scene"], 0.85)
        self.assertEqual(details["usage"], None)

    def test_score_normalizes_and_uses_half_up_level(self):
        request = self.request(
            "Score",
            "simple | static\nmedium | some overlap\ncomplex | severe overlap",
            threshold=0.7,
        )
        outputs = self.map(
            request,
            {
                "model": "jev-1.13.0",
                "answers": {
                    "decision": {
                        "type": "score",
                        "score": 1.5,
                        "legend": {
                            "0": "static",
                            "1": "some overlap",
                            "2": "severe overlap",
                        },
                        "probabilities": {"0": 0.0, "1": 0.5, "2": 0.5},
                        "confidence": 0.6,
                    }
                },
                "usage": {},
            },
            hit=True,
        )
        self.assertEqual(outputs.values(), (True, 0.75, 2, "complex"))
        details = json.loads(outputs.details_json)
        self.assertEqual(details["answer"]["score"], 1.5)
        self.assertTrue(details["cache"]["hit"])

    def test_score_low_and_high_boundaries(self):
        request = self.request("Score", "low\nhigh", threshold=1.0)
        for score, probabilities, expected in (
            (0.0, {"0": 1.0, "1": 0.0}, (False, 0.0, 0, "low")),
            (1.0, {"0": 0.0, "1": 1.0}, (True, 1.0, 1, "high")),
        ):
            with self.subTest(score=score):
                outputs = self.map(
                    request,
                    {
                        "model": "jev-test",
                        "answers": {
                            "decision": {
                                "type": "score",
                                "score": score,
                                "legend": {"0": "low", "1": "high"},
                                "probabilities": probabilities,
                                "confidence": 0.9,
                            }
                        },
                    },
                )
                self.assertEqual(outputs.values(), expected)

    def test_wrong_answer_shape_is_rejected(self):
        request = self.request("Choice", "a\nb")
        invalid = [
            {"model": "x", "answers": {"decision": {"type": "noul", "noul": 0.8}}},
            {
                "model": "x",
                "answers": {
                    "decision": {
                        "type": "choice",
                        "choice": "a",
                        "probabilities": {"a": 0.7, "b": 0.2},
                        "confidence": 0.9,
                    }
                },
            },
            {
                "model": "x",
                "answers": {
                    "decision": {
                        "type": "choice",
                        "choice": "missing",
                        "probabilities": {"a": 0.5, "b": 0.5},
                        "confidence": 0.9,
                    }
                },
            },
        ]
        for response in invalid:
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    validate_provider_response(request, response)

    def test_strict_json_rejects_duplicates_and_nonfinite_numbers(self):
        for document in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    strict_loads(document)

    def test_response_allows_unknown_fields_and_preserves_answer_extras(self):
        request = self.request("Noul")
        response = {
            "model": "jev-test",
            "answers": {
                "decision": {
                    "type": "noul",
                    "noul": 0.8,
                    "provider_note": "future metadata",
                },
                "trace": {"status": "extra question metadata"},
            },
            "usage": {"input_tokens": 10},
            "request_id": "future-top-level-field",
        }
        validated = validate_provider_response(request, response)
        self.assertEqual(
            "future metadata",
            validated["answers"]["decision"]["provider_note"],
        )
        self.assertNotIn("request_id", validated)
        self.assertNotIn("trace", validated["answers"])

        outputs = self.map(request, response)
        details = strict_loads(outputs.details_json, "details_json")
        self.assertEqual("future metadata", details["answer"]["provider_note"])

    def test_response_still_rejects_missing_required_fields(self):
        request = self.request("Noul")
        for response in (
            {"model": "jev-test", "answers": {}},
            {"answers": {"decision": {"type": "noul", "noul": 0.8}}},
            {"model": "jev-test", "answers": {"decision": {"type": "noul"}}},
        ):
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    validate_provider_response(request, response)

    def test_details_json_has_exact_v1_top_level_fields(self):
        request = self.request("Noul")
        outputs = self.map(
            request,
            {
                "model": "jev-test",
                "answers": {"decision": {"type": "noul", "noul": 0.8}},
            },
        )
        details = strict_loads(outputs.details_json, "details_json")
        self.assertEqual(
            set(details),
            {
                "schema_version",
                "kind",
                "backend",
                "requested_model",
                "model",
                "mode",
                "input_fingerprints",
                "options",
                "threshold",
                "outputs",
                "answer",
                "usage",
                "elapsed_ms",
                "cache",
            },
        )
        self.assertEqual(details["schema_version"], 1)
        self.assertEqual(details["kind"], "semantic_judge_result")


if __name__ == "__main__":
    unittest.main()
