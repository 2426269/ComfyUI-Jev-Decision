"""ComfyUI entrypoint for the Jev Decision nodepack."""

from . import decision_nodes


async def comfy_entrypoint():
    return decision_nodes.JevDecisionExtension()
