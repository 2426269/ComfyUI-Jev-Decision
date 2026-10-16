"""ComfyUI V3 adapter for the single Semantic Judge node."""

from __future__ import annotations

from typing import Any

from comfy_api.v0_0_2 import ComfyExtension, io

from .backend import DecisionService, Evaluation, TypeSafeBackend
from .decision_protocol import DecisionRequest, map_outputs


CATEGORY = "Jev Decision"
SERVICE = DecisionService(TypeSafeBackend(), capacity=256)


class JevSemanticJudge(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="JevSemanticJudge",
            display_name="Semantic Judge",
            category=CATEGORY,
            description=(
                "Turn one runtime state judgment into fixed BOOLEAN, FLOAT, INT, "
                "STRING and details_json outputs."
            ),
            inputs=[
                io.MultiType.Input(
                    "context",
                    types=[
                        io.String,
                        io.Dict,
                        io.Array,
                        io.Boolean,
                        io.Int,
                        io.Float,
                    ],
                    tooltip=(
                        "Runtime STRING, DICT, ARRAY, BOOLEAN, INT, or FLOAT. "
                        "Resource objects such as IMAGE, LATENT, and MODEL are rejected."
                    ),
                ),
                io.String.Input(
                    "instructions",
                    multiline=True,
                    default="",
                    tooltip="A complete, independent judgment instruction.",
                ),
                io.Combo.Input(
                    "mode",
                    options=["Noul", "Choice", "Score"],
                    default="Noul",
                ),
                io.String.Input(
                    "options",
                    multiline=True,
                    default="",
                    tooltip=(
                        "Choice/Score only. One option per line: "
                        "stable_id | optional description"
                    ),
                ),
                io.Float.Input(
                    "threshold",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Local BOOLEAN threshold; it is not sent to the model.",
                ),
                io.String.Input(
                    "model",
                    default="jev-latest",
                    advanced=True,
                ),
                io.String.Input(
                    "connection_profile",
                    default="default",
                    advanced=True,
                    tooltip=(
                        "Uses TYPESAFE_API_KEY, or TYPESAFE_API_KEY_<PROFILE> "
                        "for a named profile."
                    ),
                ),
                io.Int.Input(
                    "refresh",
                    default=0,
                    min=0,
                    advanced=True,
                    tooltip=(
                        "Cache-key namespace salt. Use a new value to request a new "
                        "evaluation; returning to an old value may reuse its cached result."
                    ),
                ),
            ],
            outputs=[
                io.Boolean.Output("decision"),
                io.Float.Output("value"),
                io.Int.Output("index"),
                io.String.Output("label"),
                io.String.Output("details_json"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        context: Any,
        instructions: str,
        mode: str,
        options: str,
        threshold: float,
        model: str,
        connection_profile: str,
        refresh: int,
    ) -> io.NodeOutput:
        request = DecisionRequest.create(
            context=context,
            instructions=instructions,
            mode=mode,
            options_text=options,
            threshold=threshold,
            model=model,
            connection_profile=connection_profile,
            refresh=refresh,
        )
        evaluation = await SERVICE.evaluate(request)
        outputs = map_outputs(
            request,
            evaluation.response,
            backend=SERVICE.backend.name,
            elapsed_ms=evaluation.elapsed_ms,
            cache_hit=evaluation.cache_hit,
            cache_key_sha256=evaluation.cache_key_sha256,
        )
        return io.NodeOutput(
            outputs.boolean,
            outputs.float_value,
            outputs.int_value,
            outputs.string_value,
            outputs.details_json,
        )


NODE_CLASSES = [JevSemanticJudge]


class JevDecisionExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return NODE_CLASSES
