import copy
import importlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from tests.test_nodes import n

from comfy.cli_args import args

args.cpu = True

import nodes as comfy_nodes
from comfy_api.v0_0_2 import io
from comfy_extras.nodes_preview_any import PreviewAny
from comfy_extras.nodes_primitive import Boolean as PrimitiveBoolean
from comfy_extras.nodes_primitive import StringMultiline
from comfy_extras.nodes_string import StringConcatenate
from execution import PromptExecutor, validate_prompt


EASY_USE_ROOT = Path(
    os.environ.get(
        "COMFYUI_EASY_USE_ROOT",
        str(Path(comfy_nodes.__file__).resolve().parent / "custom_nodes" / "comfyui-easy-use"),
    )
)
EASY_USE_PACKAGE = "jev_easy_use_interop_tests"
EASY_USE_IDS = (
    "easy ifElse",
    "easy compare",
    "easy anythingIndexSwitch",
    "easy showAnything",
    "easy float",
)


def load_easy_use_logic():
    existing = sys.modules.get(f"{EASY_USE_PACKAGE}.py.nodes.logic")
    if existing is not None:
        return existing
    package = types.ModuleType(EASY_USE_PACKAGE)
    package.__path__ = [str(EASY_USE_ROOT)]
    sys.modules[EASY_USE_PACKAGE] = package
    return importlib.import_module(f"{EASY_USE_PACKAGE}.py.nodes.logic")


class TrueBranchProbe:
    calls = 0

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("STRING", {"default": "true branch"})}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    CATEGORY = "Jev Decision/Tests"

    def run(self, value):
        type(self).calls += 1
        return (value,)


class FalseBranchProbe(TrueBranchProbe):
    calls = 0


class DictContext(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="JevTestDictContext", outputs=[io.Dict.Output()])

    @classmethod
    def execute(cls):
        return io.NodeOutput({"prompt": "雨夜", "count": 2})


class ArrayContext(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="JevTestArrayContext", outputs=[io.Array.Output()])

    @classmethod
    def execute(cls):
        return io.NodeOutput(["rain", {"count": 2}])


class Server:
    client_id = None

    def send_sync(self, *args, **kwargs):
        pass


class FakeBackend:
    name = "fake"

    def __init__(self, noul=0.8):
        self.calls = 0
        self.contexts = []
        self.noul = noul

    async def evaluate(self, request):
        self.calls += 1
        self.contexts.append(request.context)
        if request.mode == "Noul":
            answer = {"type": "noul", "noul": self.noul}
        elif request.mode == "Choice":
            answer = {
                "type": "choice",
                "choice": "scene",
                "probabilities": {"portrait": 0.2, "scene": 0.8},
                "confidence": 0.75,
            }
        else:
            answer = {
                "type": "score",
                "score": 1.5,
                "legend": {"0": "low", "1": "medium", "2": "high"},
                "probabilities": {"0": 0.0, "1": 0.5, "2": 0.5},
                "confidence": 0.7,
            }
        return {
            "model": "jev-fake",
            "answers": {"decision": answer},
            "usage": {"input_tokens": 8, "output_tokens": 2},
        }


def graph(
    *,
    mode="Noul",
    options="",
    threshold=0.5,
    refresh=0,
):
    prompt = {
        "0": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "runtime prompt"},
        },
        "1": {
            "class_type": "JevSemanticJudge",
            "inputs": {
                "context": ["0", 0],
                "instructions": "Make the requested judgment.",
                "mode": mode,
                "options": options,
                "threshold": threshold,
                "model": "jev-test",
                "connection_profile": "default",
                "refresh": refresh,
            },
        }
    }
    for output_index, node_id in enumerate(("2", "3", "4", "5", "6")):
        prompt[node_id] = {
            "class_type": "PreviewAny",
            "inputs": {"source": ["1", output_index]},
        }
    return prompt


def prompt_review_graph():
    boundary = (
        "\n\n<<<JEV_CONTEXT_BOUNDARY_V1: ORIGINAL ABOVE / "
        "CANDIDATE BELOW>>>\n\n"
    )
    return {
        "0": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "original prompt"},
        },
        "1": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "candidate prompt"},
        },
        "2": {
            "class_type": "StringConcatenate",
            "inputs": {
                "string_a": ["0", 0],
                "string_b": ["1", 0],
                "delimiter": boundary,
            },
        },
        "3": {
            "class_type": "JevSemanticJudge",
            "inputs": {
                "context": ["2", 0],
                "instructions": (
                    "The text before the boundary is the original prompt and the text "
                    "after it is the candidate. First enumerate every explicit subject, "
                    "count, attribute, relation, scene, composition, style, and prohibition "
                    "in the original. Then judge whether the candidate preserves every item "
                    "without contradiction or omission. Return the probability that all "
                    "requirements are preserved."
                ),
                "mode": "Noul",
                "options": "",
                "threshold": 0.8,
                "model": "jev-test",
                "connection_profile": "default",
                "refresh": 0,
            },
        },
        "4": {"class_type": "easy float", "inputs": {"value": 0.5}},
        "5": {"class_type": "easy float", "inputs": {"value": 0.8}},
        "6": {
            "class_type": "easy compare",
            "inputs": {
                "a": ["3", 1],
                "b": ["4", 0],
                "comparison": "a >= b",
            },
        },
        "7": {
            "class_type": "easy compare",
            "inputs": {
                "a": ["3", 1],
                "b": ["5", 0],
                "comparison": "a >= b",
            },
        },
        "8": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "adopt"},
        },
        "9": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "review"},
        },
        "10": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "reject"},
        },
        "11": {
            "class_type": "easy ifElse",
            "inputs": {
                "boolean": ["6", 0],
                "on_true": ["9", 0],
                "on_false": ["10", 0],
            },
        },
        "12": {
            "class_type": "easy ifElse",
            "inputs": {
                "boolean": ["7", 0],
                "on_true": ["8", 0],
                "on_false": ["11", 0],
            },
        },
        "13": {
            "class_type": "easy ifElse",
            "inputs": {
                "boolean": ["7", 0],
                "on_true": ["1", 0],
                "on_false": ["0", 0],
            },
        },
        "14": {
            "class_type": "easy showAnything",
            "inputs": {"anything": ["12", 0]},
        },
        "15": {
            "class_type": "easy showAnything",
            "inputs": {"anything": ["13", 0]},
        },
        "16": {
            "class_type": "easy showAnything",
            "inputs": {"anything": ["3", 1]},
        },
        "17": {
            "class_type": "easy showAnything",
            "inputs": {"anything": ["3", 4]},
        },
    }


class ComfyExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.saved_nodes = dict(comfy_nodes.NODE_CLASS_MAPPINGS)
        for node_class in await n.JevDecisionExtension().get_node_list():
            schema = node_class.GET_SCHEMA()
            comfy_nodes.NODE_CLASS_MAPPINGS[schema.node_id] = node_class
        comfy_nodes.NODE_CLASS_MAPPINGS["PreviewAny"] = PreviewAny
        comfy_nodes.NODE_CLASS_MAPPINGS["PrimitiveStringMultiline"] = (
            StringMultiline
        )
        comfy_nodes.NODE_CLASS_MAPPINGS["StringConcatenate"] = StringConcatenate
        comfy_nodes.NODE_CLASS_MAPPINGS["PrimitiveBoolean"] = PrimitiveBoolean
        comfy_nodes.NODE_CLASS_MAPPINGS["JevTestTrueBranch"] = TrueBranchProbe
        comfy_nodes.NODE_CLASS_MAPPINGS["JevTestFalseBranch"] = FalseBranchProbe
        comfy_nodes.NODE_CLASS_MAPPINGS["JevTestDictContext"] = DictContext
        comfy_nodes.NODE_CLASS_MAPPINGS["JevTestArrayContext"] = ArrayContext
        TrueBranchProbe.calls = 0
        FalseBranchProbe.calls = 0

    async def asyncTearDown(self):
        comfy_nodes.NODE_CLASS_MAPPINGS.clear()
        comfy_nodes.NODE_CLASS_MAPPINGS.update(self.saved_nodes)

    async def run_graph(self, executor, prompt, prompt_id):
        valid, error, outputs, details = await validate_prompt(prompt_id, prompt, None)
        self.assertTrue(valid, (error, details))
        self.assertFalse(details, details)
        await executor.execute_async(prompt, prompt_id, execute_outputs=outputs)
        self.assertTrue(executor.success, executor.status_messages)
        return await executor.caches.outputs.get("1")

    async def test_threshold_reuses_backend_response_and_refresh_calls_again(self):
        fake = FakeBackend()
        service = n.DecisionService(fake, capacity=8)
        executor = PromptExecutor(
            Server(),
            cache_type=False,
            cache_args={"ram": 0, "ram_inactive": 0},
        )
        with patch.object(n, "SERVICE", service):
            first = await self.run_graph(
                executor,
                copy.deepcopy(graph(threshold=0.5)),
                "first",
            )
            self.assertEqual(first.outputs[0][0], True)
            self.assertEqual(first.outputs[1][0], 0.8)
            self.assertEqual(fake.calls, 1)

            threshold_only = await self.run_graph(
                executor,
                copy.deepcopy(graph(threshold=0.9)),
                "threshold",
            )
            self.assertEqual(threshold_only.outputs[0][0], False)
            self.assertEqual(fake.calls, 1)

            await self.run_graph(
                executor,
                copy.deepcopy(graph(threshold=0.9, refresh=1)),
                "refresh",
            )
            self.assertEqual(fake.calls, 2)

    async def test_all_modes_execute_with_fixed_outputs(self):
        fake = FakeBackend()
        service = n.DecisionService(fake, capacity=8)
        executor = PromptExecutor(
            Server(),
            cache_type=False,
            cache_args={"ram": 0, "ram_inactive": 0},
        )
        cases = [
            ("Noul", "", (True, 0.8, 1, "true")),
            (
                "Choice",
                "portrait | close subject\nscene | large environment",
                (True, 0.75, 1, "scene"),
            ),
            (
                "Score",
                "simple | low\nmedium | medium\ncomplex | high",
                (True, 0.75, 2, "complex"),
            ),
        ]
        with patch.object(n, "SERVICE", service):
            for index, (mode, options, expected) in enumerate(cases):
                cached = await self.run_graph(
                    executor,
                    copy.deepcopy(
                        graph(
                            mode=mode,
                            options=options,
                            threshold=0.5,
                        )
                    ),
                    f"mode-{index}",
                )
                actual = tuple(cached.outputs[position][0] for position in range(4))
                self.assertEqual(actual, expected)
                self.assertIsInstance(cached.outputs[4][0], str)
        self.assertEqual(fake.calls, 3)

    async def test_multitype_context_executes_as_native_json_state(self):
        cases = [
            ("JevTestDictContext", {}, {"prompt": "雨夜", "count": 2}),
            ("JevTestArrayContext", {}, ["rain", {"count": 2}]),
            ("PrimitiveBoolean", {"value": False}, {"value": False}),
        ]
        for index, (class_type, inputs, expected) in enumerate(cases):
            fake = FakeBackend()
            service = n.DecisionService(fake, capacity=8)
            executor = PromptExecutor(
                Server(),
                cache_type=False,
                cache_args={"ram": 0, "ram_inactive": 0},
            )
            prompt = graph()
            prompt["0"] = {"class_type": class_type, "inputs": inputs}
            with patch.object(n, "SERVICE", service):
                await self.run_graph(executor, prompt, f"context-type-{index}")
            self.assertEqual(fake.contexts, [expected])

    async def test_actual_easy_use_consumers_and_lazy_if_else(self):
        if not EASY_USE_ROOT.is_dir():
            self.skipTest(
                "comfyui-easy-use is not installed; set COMFYUI_EASY_USE_ROOT "
                "to run the optional interoperability test"
            )
        easy_logic = load_easy_use_logic()
        missing = [node_id for node_id in EASY_USE_IDS if node_id not in easy_logic.NODE_CLASS_MAPPINGS]
        if missing:
            self.skipTest(f"comfyui-easy-use is missing required nodes: {missing}")
        for node_id in EASY_USE_IDS:
            comfy_nodes.NODE_CLASS_MAPPINGS[node_id] = easy_logic.NODE_CLASS_MAPPINGS[node_id]
        fake = FakeBackend()
        service = n.DecisionService(fake, capacity=8)
        executor = PromptExecutor(
            Server(),
            cache_type=False,
            cache_args={"ram": 0, "ram_inactive": 0},
        )
        prompt = {
            "0": {
                "class_type": "PrimitiveStringMultiline",
                "inputs": {"value": "runtime prompt"},
            },
            "1": {
                "class_type": "JevSemanticJudge",
                "inputs": {
                    "context": ["0", 0],
                    "instructions": "Choose a route.",
                    "mode": "Choice",
                    "options": "portrait | close subject\nscene | large environment",
                    "threshold": 0.5,
                    "model": "jev-test",
                    "connection_profile": "default",
                    "refresh": 0,
                },
            },
            "2": {
                "class_type": "JevTestTrueBranch",
                "inputs": {"value": "selected true branch"},
            },
            "3": {
                "class_type": "JevTestFalseBranch",
                "inputs": {"value": "unselected false branch"},
            },
            "4": {
                "class_type": "easy ifElse",
                "inputs": {
                    "boolean": ["1", 0],
                    "on_true": ["2", 0],
                    "on_false": ["3", 0],
                },
            },
            "5": {
                "class_type": "easy compare",
                "inputs": {
                    "a": ["1", 1],
                    "b": ["12", 0],
                    "comparison": "a >= b",
                },
            },
            "6": {
                "class_type": "easy anythingIndexSwitch",
                "inputs": {
                    "index": ["1", 2],
                    "value0": ["1", 3],
                    "value1": ["1", 4],
                },
            },
            "12": {
                "class_type": "easy float",
                "inputs": {"value": 0.7},
            },
        }
        for node_id, source in {
            "7": ["1", 3],
            "8": ["1", 4],
            "9": ["4", 0],
            "10": ["5", 0],
            "11": ["6", 0],
        }.items():
            prompt[node_id] = {
                "class_type": "easy showAnything",
                "inputs": {"anything": source},
            }

        with patch.object(n, "SERVICE", service):
            await self.run_graph(executor, prompt, "easy-use-interop")

        self.assertEqual(fake.calls, 1)
        self.assertEqual(TrueBranchProbe.calls, 1)
        self.assertEqual(FalseBranchProbe.calls, 0)
        if_else = await executor.caches.outputs.get("4")
        compare = await executor.caches.outputs.get("5")
        index_switch = await executor.caches.outputs.get("6")
        self.assertEqual(if_else.outputs[0][0], "selected true branch")
        self.assertEqual(compare.outputs[0][0], True)
        details = index_switch.outputs[0][0]
        self.assertEqual(json.loads(details)["schema_version"], 1)

    async def test_prompt_review_recipe_routes_three_states_and_falls_back(self):
        if not EASY_USE_ROOT.is_dir():
            self.skipTest(
                "comfyui-easy-use is not installed; set COMFYUI_EASY_USE_ROOT "
                "to run the optional recipe test"
            )
        easy_logic = load_easy_use_logic()
        required = ("easy ifElse", "easy compare", "easy showAnything", "easy float")
        missing = [node_id for node_id in required if node_id not in easy_logic.NODE_CLASS_MAPPINGS]
        if missing:
            self.skipTest(f"comfyui-easy-use is missing required nodes: {missing}")
        for node_id in required:
            comfy_nodes.NODE_CLASS_MAPPINGS[node_id] = easy_logic.NODE_CLASS_MAPPINGS[node_id]

        cases = (
            (0.90, "adopt", "candidate prompt", False),
            (0.65, "review", "original prompt", True),
            (0.20, "reject", "original prompt", True),
        )
        boundary = (
            "\n\n<<<JEV_CONTEXT_BOUNDARY_V1: ORIGINAL ABOVE / "
            "CANDIDATE BELOW>>>\n\n"
        )
        for index, (probability, route, selected, inner_used) in enumerate(cases):
            with self.subTest(probability=probability):
                fake = FakeBackend(noul=probability)
                service = n.DecisionService(fake, capacity=8)
                executor = PromptExecutor(
                    Server(),
                    cache_type=False,
                    cache_args={"ram": 0, "ram_inactive": 0},
                )
                with patch.object(n, "SERVICE", service):
                    await self.run_graph(
                        executor,
                        prompt_review_graph(),
                        f"prompt-review-{index}",
                    )

                self.assertEqual(fake.calls, 1)
                self.assertEqual(
                    fake.contexts,
                    [f"original prompt{boundary}candidate prompt"],
                )
                route_output = await executor.caches.outputs.get("12")
                selected_output = await executor.caches.outputs.get("13")
                inner_output = await executor.caches.outputs.get("11")
                self.assertEqual(route_output.outputs[0][0], route)
                self.assertEqual(selected_output.outputs[0][0], selected)
                self.assertEqual(inner_output is not None, inner_used)


if __name__ == "__main__":
    unittest.main()
