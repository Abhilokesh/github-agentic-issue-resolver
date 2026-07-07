"""Per-issue resolution pipeline: Triage -> (Code -> Test -> Review) retried
up to MAX_ITERATIONS -> PR draft.

Built on ADK's dynamic-workflow pattern (@node + ctx.run_node) rather than
the deprecated SequentialAgent/LoopAgent classes -- confirmed via ADK's own
docs as the currently recommended approach for exactly this shape of
problem (a retry loop with an early-exit condition).
"""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.runners import InMemoryRunner
from google.adk.workflow import node
from google.genai import types

from .sub_agents.coding_agent import coding_agent
from .sub_agents.pr_agent import pr_agent
from .sub_agents.review_agent import review_agent
from .sub_agents.test_runner_node import test_runner_node
from .sub_agents.triage_agent import triage_agent
from .tools.llm_backoff import run_node_with_backoff

MAX_ITERATIONS = 3

triage_node = node(triage_agent, rerun_on_resume=True)
coding_node = node(coding_agent, rerun_on_resume=True)
review_node = node(review_agent, rerun_on_resume=True)
pr_node = node(pr_agent, rerun_on_resume=True)


def _issue_prompt(issue: dict) -> str:
    return (
        f"Issue: {issue['title']}\n\n{issue['description']}\n\n"
        f"(hint: likely relevant path: {issue.get('target_hint', 'unknown')})"
    )


@node(rerun_on_resume=True)
async def resolve_issue_workflow(ctx: Context, issue: dict) -> dict:
    """`issue`: one entry from sandbox_repo/issues.yaml (id, title,
    description, category, oracle_cmd, target_hint), bound from session
    state -- see run_for_issue() below for how it's passed in."""
    triage_summary = await run_node_with_backoff(ctx, triage_node, _issue_prompt(issue))

    patch = ""
    test_result: dict = {}
    review_verdict = ""
    resolved = False
    feedback = ""
    attempt = 0

    for attempt in range(1, MAX_ITERATIONS + 1):
        coding_prompt = (
            f"{_issue_prompt(issue)}\n\nTriage notes: {triage_summary}\n{feedback}"
        )
        patch = await run_node_with_backoff(ctx, coding_node, coding_prompt)
        # test_runner_node is deterministic, not an LLM call -- no backoff needed.
        test_result = await ctx.run_node(
            test_runner_node, {"patch": patch, "oracle_cmd": issue["oracle_cmd"]}
        )

        if not test_result.get("guard_passed"):
            feedback = (
                "\nYour previous patch was REJECTED before testing: "
                f"{test_result.get('guard_reason')}. Do not do this again."
            )
            continue

        if not test_result.get("applied"):
            feedback = (
                "\nYour previous patch failed to apply cleanly: "
                f"{test_result.get('apply_error')}. Re-read the file with "
                "read_repo_file and produce a valid unified diff against its "
                "exact current content."
            )
            continue

        if not test_result.get("oracle_passed"):
            feedback = (
                "\nYour previous patch applied but the check still fails.\n"
                f"stdout:\n{test_result.get('stdout')}\n"
                f"stderr:\n{test_result.get('stderr')}\n"
                "Fix the remaining problem."
            )
            continue

        review_prompt = (
            f"{_issue_prompt(issue)}\n\nPatch:\n{patch}\n\n"
            "The automated check now passes."
        )
        review_verdict = await run_node_with_backoff(ctx, review_node, review_prompt)
        if review_verdict.strip().upper().startswith("APPROVED"):
            resolved = True
            break
        feedback = (
            f"\nCode review rejected your patch: {review_verdict}\n"
            "Address this feedback."
        )

    pr_draft = ""
    if resolved:
        pr_prompt = f"{_issue_prompt(issue)}\n\nPatch:\n{patch}"
        pr_draft = await run_node_with_backoff(ctx, pr_node, pr_prompt)

    return {
        "issue_id": issue.get("id"),
        "resolved": resolved,
        "attempts": attempt,
        "patch": patch,
        "test_result": test_result,
        "review_verdict": review_verdict,
        "pr_draft": pr_draft,
    }


async def run_for_issue(issue: dict, app_name: str = "github_issue_agent") -> dict:
    """Shared entrypoint for the benchmark harness, CLI, and tests: runs the
    resolve_issue_workflow for one issue dict and returns its final result.
    """
    runner = InMemoryRunner(node=resolve_issue_workflow, app_name=app_name)
    session = await runner.session_service.create_session(
        app_name=app_name, user_id="agent", state={"issue": issue}
    )

    result = None
    async for event in runner.run_async(
        user_id="agent",
        session_id=session.id,
        new_message=types.Content(parts=[types.Part(text="resolve this issue")]),
    ):
        if event.output is not None:
            result = event.output
    return result
