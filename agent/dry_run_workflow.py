"""Real-issue dry-run pipeline: Triage -> (Code -> regression-check) retried
up to max_attempts -> Review. Separate from agent/coordinator.py on
purpose -- that pipeline is tuned for the benchmark's precise oracle_cmd
per issue, which doesn't exist for an arbitrary real GitHub issue.

Verification here is honestly weaker than the benchmark: with a
`test_cmd`, it's a regression check (the repo's own test suite must not
have any test flip from passing to failing) rather than a proof the
described bug is fixed. Without a `test_cmd`, there's no test signal at
all and the result relies solely on ReviewAgent's judgment -- this is
always labeled `verified: false` in the result, never conflated with the
benchmark's oracle-verified results.

This module never touches any GitHub write action. Fetching the issue and
(if approved) opening a PR both happen in agent/cli.py, using the GitHub
MCP toolset directly -- same separation the existing benchmark/demo-mode
split already uses (agent/coordinator.py never calls GitHub either).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from google.adk.agents.context import Context
from google.adk.runners import InMemoryRunner
from google.adk.workflow import node
from google.genai import types

from .sub_agents.coding_agent import build_coding_agent
from .sub_agents.pr_agent import pr_agent
from .sub_agents.review_agent import review_agent
from .sub_agents.triage_agent import build_triage_agent
from .tools.generic_test_check import diff_test_results, run_tests_and_parse
from .tools.llm_backoff import run_node_with_backoff
from .tools.patch_tools import changed_files
from .tools.repo_clone import clone_repo
from .tools.sandbox_exec import run_in_sandbox
from .tools.test_env import prepare_test_env

review_node = node(review_agent, rerun_on_resume=True)
pr_node = node(pr_agent, rerun_on_resume=True)


def _issue_prompt(params: dict) -> str:
    return (
        f"Issue: {params['issue_title']}\n\n{params['issue_body']}\n\n"
        f"(repository: {params['owner']}/{params['repo']})"
    )


@node(rerun_on_resume=True)
async def try_real_issue_workflow(ctx: Context, params: dict) -> dict:
    """`params`: owner, repo, issue_number, issue_title, issue_body,
    test_cmd (optional), target_test (optional), max_attempts (default 2).
    Bound from session state -- see run_for_real_issue() below."""
    project_name = f"the `{params['owner']}/{params['repo']}` GitHub repository"
    triage_node = node(build_triage_agent(project_name), rerun_on_resume=True)

    clone_dir = Path(tempfile.mkdtemp(prefix="real_issue_clone_"))
    try:
        clone_repo(params["owner"], params["repo"], clone_dir)
        coding_node = node(
            build_coding_agent(project_name, clone_dir), rerun_on_resume=True
        )

        test_cmd = params.get("test_cmd")
        python_bin = None
        before_results: dict[str, str] = {}
        install_error = None
        if test_cmd:
            python_bin, install_error = prepare_test_env(clone_dir)
            if not install_error:
                before_results = run_tests_and_parse(python_bin, clone_dir, test_cmd)

        triage_summary = await run_node_with_backoff(
            ctx, triage_node, _issue_prompt(params)
        )

        max_attempts = params.get("max_attempts", 2)
        patch = ""
        review_verdict = ""
        resolved = False
        final_verified = False
        regression_report: dict = {}
        feedback = ""
        attempt = 0

        for attempt in range(1, max_attempts + 1):
            coding_prompt = (
                f"{_issue_prompt(params)}\n\nTriage notes: {triage_summary}\n{feedback}"
            )
            patch = await run_node_with_backoff(ctx, coding_node, coding_prompt)

            apply_result = run_in_sandbox(patch, "true", repo_root=clone_dir)
            if not apply_result["guard_passed"]:
                feedback = (
                    "\nYour previous patch was REJECTED before testing: "
                    f"{apply_result['guard_reason']}. Do not do this again."
                )
                continue
            if not apply_result["applied"]:
                feedback = (
                    "\nYour previous patch failed to apply cleanly: "
                    f"{apply_result['apply_error']}. Re-read the file with "
                    "read_repo_file and produce a valid unified diff against "
                    "its exact current content."
                )
                continue

            verified = False
            if test_cmd and python_bin and not install_error:
                patched_copy = Path(tempfile.mkdtemp(prefix="real_issue_patched_"))
                try:
                    shutil.copytree(clone_dir, patched_copy, dirs_exist_ok=True)
                    patch_file = patched_copy / "_candidate.patch"
                    patch_file.write_text(patch)
                    subprocess.run(
                        ["git", "apply", "--whitespace=nowarn", str(patch_file)],
                        cwd=patched_copy,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    patch_file.unlink(missing_ok=True)
                    after_results = run_tests_and_parse(python_bin, patched_copy, test_cmd)
                    regression_report = diff_test_results(before_results, after_results)
                    target_test = params.get("target_test")
                    target_ok = (
                        after_results.get(target_test) == "PASSED"
                        if target_test
                        else bool(regression_report["newly_fixed"])
                    )
                    if regression_report["regressions"]:
                        feedback = (
                            "\nYour patch applied, but it broke previously-passing "
                            f"tests: {regression_report['regressions']}. Fix this "
                            "without breaking existing behavior."
                        )
                        continue
                    if not target_ok:
                        feedback = (
                            "\nYour patch applied and didn't break anything, but "
                            "didn't appear to fix the issue (no previously-failing "
                            "test now passes). Reconsider the fix."
                        )
                        continue
                    verified = True
                finally:
                    shutil.rmtree(patched_copy, ignore_errors=True)

            final_verified = verified
            review_prompt = (
                f"{_issue_prompt(params)}\n\nPatch:\n{patch}\n\n"
                + (
                    "The repo's test suite shows the fix works with no regressions."
                    if verified
                    else "No automated test verification was possible for this "
                    "patch -- judge it on the diff and issue description alone."
                )
            )
            review_verdict = await run_node_with_backoff(ctx, review_node, review_prompt)
            if review_verdict.strip().upper().startswith("APPROVED"):
                resolved = True
                break
            feedback = (
                f"\nCode review rejected your patch: {review_verdict}\nAddress this feedback."
            )

        pr_draft = ""
        if resolved:
            pr_prompt = f"{_issue_prompt(params)}\n\nPatch:\n{patch}"
            pr_draft = await run_node_with_backoff(ctx, pr_node, pr_prompt)

        return {
            "resolved": resolved,
            "verified": final_verified,
            "attempts": attempt,
            "patch": patch,
            "changed_files": changed_files(patch) if patch else [],
            "review_verdict": review_verdict,
            "pr_draft": pr_draft,
            "regression_report": regression_report,
            "install_error": install_error,
        }
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


async def run_for_real_issue(params: dict, app_name: str = "real_issue_dry_run") -> dict:
    """Shared entrypoint, mirrors agent/coordinator.py::run_for_issue."""
    runner = InMemoryRunner(node=try_real_issue_workflow, app_name=app_name)
    session = await runner.session_service.create_session(
        app_name=app_name, user_id="agent", state={"params": params}
    )

    result = None
    async for event in runner.run_async(
        user_id="agent",
        session_id=session.id,
        new_message=types.Content(parts=[types.Part(text="try this issue")]),
    ):
        if event.output is not None:
            result = event.output
    return result
