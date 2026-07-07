"""Not an LlmAgent on purpose: applying a patch and checking pass/fail is a
deterministic operation, so it runs as plain code rather than spending a
model call on something an LLM would just be slower and less reliable at.
"""

from __future__ import annotations

import asyncio

from google.adk.agents.context import Context
from google.adk.workflow import node

from ..tools.sandbox_exec import run_in_sandbox


@node(rerun_on_resume=True)
async def test_runner_node(ctx: Context, node_input: dict) -> dict:
    return await asyncio.to_thread(
        run_in_sandbox, node_input["patch"], node_input["oracle_cmd"]
    )
