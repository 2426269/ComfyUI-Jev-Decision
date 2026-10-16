import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

import torch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "jev_decision_nodepack"


def load_nodepack():
    existing = sys.modules.get(PACKAGE_NAME)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)
    return module


nodepack = load_nodepack()
n = nodepack.decision_nodes


class SchemaTests(unittest.TestCase):
    def test_only_semantic_judge_is_registered(self):
        self.assertEqual(len(n.NODE_CLASSES), 1)
        schema = n.NODE_CLASSES[0].define_schema()
        self.assertEqual(schema.node_id, "JevSemanticJudge")
        schema.finalize()
        schema.validate()

    def test_schema_has_fixed_inputs_and_outputs(self):
        schema = n.JevSemanticJudge.define_schema()
        self.assertEqual(
            [item.id for item in schema.inputs],
            [
                "context",
                "instructions",
                "mode",
                "options",
                "threshold",
                "model",
                "connection_profile",
                "refresh",
            ],
        )
        self.assertEqual(
            [(item.id, item.get_io_type()) for item in schema.outputs],
            [
                ("decision", "BOOLEAN"),
                ("value", "FLOAT"),
                ("index", "INT"),
                ("label", "STRING"),
                ("details_json", "STRING"),
            ],
        )
        context, instructions = schema.inputs[:2]
        self.assertEqual(
            context.get_io_type(),
            "STRING,DICT,ARRAY,BOOLEAN,INT,FLOAT",
        )
        self.assertIsNone(instructions.force_input)


class FakeService:
    def __init__(self, response):
        self.backend = type("Backend", (), {"name": "fake"})()
        self.evaluate = AsyncMock(return_value=response)


class NodeExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_noul_node_returns_five_outputs(self):
        evaluation = n.Evaluation(
            response={
                "model": "jev-test",
                "answers": {"decision": {"type": "noul", "noul": 0.8}},
                "usage": {"input_tokens": 5, "output_tokens": 1},
            },
            cache_hit=False,
            cache_key_sha256="b" * 64,
            elapsed_ms=9,
        )
        service = FakeService(evaluation)
        with patch.object(n, "SERVICE", service):
            output = await n.JevSemanticJudge.execute(
                context="runtime prompt",
                instructions="Does it preserve the meaning?",
                mode="Noul",
                options="",
                threshold=0.75,
                model="jev-latest",
                connection_profile="default",
                refresh=0,
            )

        self.assertEqual(output.result[:4], (True, 0.8, 1, "true"))
        details = json.loads(output.result[4])
        self.assertEqual(details["model"], "jev-test")
        request = service.evaluate.await_args.args[0]
        self.assertEqual(request.context, "runtime prompt")
        self.assertEqual(request.threshold, 0.75)

    async def test_choice_node_keeps_declared_index(self):
        evaluation = n.Evaluation(
            response={
                "model": "jev-test",
                "answers": {
                    "decision": {
                        "type": "choice",
                        "choice": "scene",
                        "probabilities": {"portrait": 0.2, "scene": 0.8},
                        "confidence": 0.7,
                    }
                },
                "usage": None,
            },
            cache_hit=True,
            cache_key_sha256="c" * 64,
            elapsed_ms=0,
        )
        service = FakeService(evaluation)
        with patch.object(n, "SERVICE", service):
            output = await n.JevSemanticJudge.execute(
                context="runtime prompt",
                instructions="Choose a route.",
                mode="Choice",
                options="portrait | close subject\nscene | large environment",
                threshold=0.8,
                model="jev-latest",
                connection_profile="default",
                refresh=0,
            )

        self.assertEqual(output.result[:4], (False, 0.7, 1, "scene"))
        self.assertTrue(json.loads(output.result[4])["cache"]["hit"])

    async def test_node_wraps_scalar_context_before_backend(self):
        evaluation = n.Evaluation(
            response={
                "model": "jev-test",
                "answers": {"decision": {"type": "noul", "noul": 0.8}},
                "usage": None,
            },
            cache_hit=False,
            cache_key_sha256="d" * 64,
            elapsed_ms=1,
        )
        service = FakeService(evaluation)
        with patch.object(n, "SERVICE", service):
            await n.JevSemanticJudge.execute(
                context=False,
                instructions="Judge this value.",
                mode="Noul",
                options="",
                threshold=0.5,
                model="jev-latest",
                connection_profile="default",
                refresh=0,
            )
        self.assertEqual(service.evaluate.await_args.args[0].context, {"value": False})

    async def test_invalid_runtime_objects_fail_before_backend(self):
        service = FakeService(None)
        for context in (None, torch.zeros(1), {"tensor": torch.zeros(1)}):
            with self.subTest(kind=type(context).__name__):
                with patch.object(n, "SERVICE", service):
                    with self.assertRaises(ValueError):
                        await n.JevSemanticJudge.execute(
                            context=context,
                            instructions="Judge this value.",
                            mode="Noul",
                            options="",
                            threshold=0.5,
                            model="jev-latest",
                            connection_profile="default",
                            refresh=0,
                        )
        service.evaluate.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
