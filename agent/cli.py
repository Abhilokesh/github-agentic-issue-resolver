"""Demo-mode CLI: resolve one issue through the full pipeline, then --
only after an explicit human confirmation -- push a branch and open a
real PR against SANDBOX_REPO via the GitHub MCP server.

    python3 -m agent.cli resolve --issue-id B1

This is deliberately separate from benchmark/run_benchmark.py, which
never touches GitHub at all.

A second subcommand, `try-real-issue`, runs the weaker-verification
dry-run pipeline (agent/dry_run_workflow.py) against an arbitrary real
GitHub issue, and -- again only after explicit human confirmation --
forks the repo, pushes a branch to the fork, and opens a PR back to the
upstream project:

    python3 -m agent.cli try-real-issue --repo owner/name --issue 123 \\
        --test-cmd "pytest -v"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

from .coordinator import run_for_issue  # noqa: E402
from .dry_run_workflow import run_for_real_issue  # noqa: E402
from .tools.github_mcp import build_github_toolset  # noqa: E402
from .tools.repo_clone import clone_repo  # noqa: E402

ISSUES_YAML = REPO_ROOT / "sandbox_repo" / "issues.yaml"
REAL_ISSUE_ATTEMPTS_DIR = REPO_ROOT / "real_issue_attempts"


def _mcp_json(result: dict):
    """MCP tool results come back as `{"content": [{"type": "text", "text":
    "<json>"}], ...}` for this server -- unwrap to the actual payload.

    Confirmed empirically: ADK's MCP graceful-error-handling wraps a failed
    call (bad token, 404, etc.) into a flat `{"error": "..."}` dict instead
    of the raw MCP isError/content shape -- checked for explicitly here.
    The success-path content-list shape is a documented assumption, not
    yet exercised against a real token (see plan verification step 4): if
    the server ever returns something shaped differently, this raises
    rather than silently misparsing.
    """
    if "error" in result:
        raise RuntimeError(f"GitHub MCP tool call failed: {result['error']}")
    if result.get("isError"):
        raise RuntimeError(f"GitHub MCP tool call failed: {result}")
    content = result.get("content") or []
    for block in content:
        if block.get("type") == "text":
            return json.loads(block["text"])
    raise RuntimeError(f"Unexpected GitHub MCP response shape: {result}")


def _load_issue(issue_id: str) -> dict:
    issues = yaml.safe_load(ISSUES_YAML.read_text())["issues"]
    try:
        return next(i for i in issues if i["id"] == issue_id)
    except StopIteration:
        raise SystemExit(f"Unknown issue id: {issue_id!r}")


async def _open_pull_request(issue: dict, outcome: dict) -> None:
    """Only called after the human has explicitly confirmed."""
    sandbox_repo = os.environ.get("SANDBOX_REPO")
    if not sandbox_repo:
        raise SystemExit(
            "SANDBOX_REPO is not set in .env -- required to open a real PR. "
            "See .env.example."
        )

    toolset = build_github_toolset()
    try:
        tools = {t.name: t for t in await toolset.get_tools()}
        owner, repo = sandbox_repo.split("/", 1)
        branch = f"agent/{issue['id'].lower()}"

        print(f"Creating branch '{branch}' on {sandbox_repo} ...")
        await tools["create_branch"].run_async(
            args={"owner": owner, "repo": repo, "branch": branch},
            tool_context=None,
        )

        title, _, body = outcome["pr_draft"].partition("\n\n")
        print("Opening pull request ...")
        result = await tools["create_pull_request"].run_async(
            args={
                "owner": owner,
                "repo": repo,
                "title": title.strip() or f"Fix {issue['id']}: {issue['title']}",
                "head": branch,
                "base": "main",
                "body": body.strip() or outcome["pr_draft"],
            },
            tool_context=None,
        )
        print("PR created:", result)
    finally:
        await toolset.close()


async def _open_real_pr(
    owner: str, repo: str, issue_number: int, patch: str, changed_files: list[str], pr_draft: str
) -> dict:
    """Only called after explicit human confirmation. Forks the repo,
    pushes a branch to the fork with the patched files, and opens a PR
    from the fork back to upstream -- never pushes to `owner/repo` itself.
    """
    toolset = build_github_toolset("GITHUB_PAT_BROAD")
    try:
        tools = {t.name: t for t in await toolset.get_tools()}

        print(f"Forking {owner}/{repo} ...")
        fork_result = _mcp_json(
            await tools["fork_repository"].run_async(
                args={"owner": owner, "repo": repo}, tool_context=None
            )
        )
        fork_owner = fork_result["owner"]["login"]
        fork_name = fork_result["name"]
        default_branch = fork_result.get("default_branch", "main")

        branch = f"agent/fix-issue-{issue_number}"
        print(f"Creating branch '{branch}' on {fork_owner}/{fork_name} ...")
        await tools["create_branch"].run_async(
            args={"owner": fork_owner, "repo": fork_name, "branch": branch},
            tool_context=None,
        )

        # Apply the already-approved patch to a fresh clone to read back
        # the final file content push_files needs (it takes full content,
        # not diffs).
        clone_dir = Path(tempfile.mkdtemp(prefix="real_issue_push_"))
        try:
            clone_repo(owner, repo, clone_dir)
            patch_file = clone_dir / "_approved.patch"
            patch_file.write_text(patch)
            subprocess.run(
                ["git", "apply", "--whitespace=nowarn", str(patch_file)],
                cwd=clone_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            files_payload = [
                {"path": f, "content": (clone_dir / f).read_text()} for f in changed_files
            ]
        finally:
            shutil.rmtree(clone_dir, ignore_errors=True)

        print(f"Pushing {len(files_payload)} file(s) to {fork_owner}/{fork_name}@{branch} ...")
        await tools["push_files"].run_async(
            args={
                "owner": fork_owner,
                "repo": fork_name,
                "branch": branch,
                "files": files_payload,
                "message": f"Fix issue #{issue_number}",
            },
            tool_context=None,
        )

        title, _, body = pr_draft.partition("\n\n")
        print(f"Opening PR against {owner}/{repo} ...")
        pr_result = _mcp_json(
            await tools["create_pull_request"].run_async(
                args={
                    "owner": owner,
                    "repo": repo,
                    "title": title.strip() or f"Fix issue #{issue_number}",
                    "head": f"{fork_owner}:{branch}",
                    "base": default_branch,
                    "body": body.strip() or pr_draft,
                },
                tool_context=None,
            )
        )
        return pr_result
    finally:
        await toolset.close()


async def cmd_try_real_issue(
    repo: str,
    issue_number: int,
    test_cmd: str | None,
    target_test: str | None,
    max_attempts: int,
    auto_approve: bool,
) -> None:
    owner, name = repo.split("/", 1)

    toolset = build_github_toolset("GITHUB_PAT_BROAD")
    try:
        tools = {t.name: t for t in await toolset.get_tools()}
        print(f"Fetching issue #{issue_number} from {repo} ...")
        issue_data = _mcp_json(
            await tools["issue_read"].run_async(
                args={
                    "owner": owner,
                    "repo": name,
                    "issue_number": issue_number,
                    "method": "get",
                },
                tool_context=None,
            )
        )
    finally:
        await toolset.close()

    params = {
        "owner": owner,
        "repo": name,
        "issue_number": issue_number,
        "issue_title": issue_data["title"],
        "issue_body": issue_data.get("body") or "(no description provided)",
        "test_cmd": test_cmd,
        "target_test": target_test,
        "max_attempts": max_attempts,
    }
    print(f"Issue: {params['issue_title']}\n")

    outcome = await run_for_real_issue(params)

    print("=" * 60)
    print(f"Resolved: {outcome['resolved']}  (verified: {outcome['verified']}, "
          f"attempts: {outcome['attempts']})")
    if outcome["install_error"]:
        print(f"NOTE: dependency install failed, no test verification was possible:\n"
              f"{outcome['install_error'][:500]}")
    print("-" * 60)
    print("Patch:\n", outcome["patch"])
    print("-" * 60)
    print("Review verdict:", outcome["review_verdict"])
    if outcome["regression_report"]:
        print("Regression check:", outcome["regression_report"])
    if outcome["pr_draft"]:
        print("-" * 60)
        print("PR draft:\n", outcome["pr_draft"])
    print("=" * 60)

    run_dir = REAL_ISSUE_ATTEMPTS_DIR / f"{owner}-{name}-{issue_number}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "patch.diff").write_text(outcome["patch"])
    (run_dir / "RESULT.md").write_text(
        f"# {owner}/{name} issue #{issue_number}\n\n"
        f"resolved: {outcome['resolved']}\n"
        f"verified: {outcome['verified']}\n"
        f"attempts: {outcome['attempts']}\n\n"
        f"## Review verdict\n{outcome['review_verdict']}\n\n"
        f"## PR draft\n{outcome['pr_draft']}\n\n"
        f"## Regression report\n{outcome['regression_report']}\n"
    )
    print(f"\nSaved local copy -> {run_dir}/")

    if not outcome["resolved"]:
        print("Issue was not resolved -- not opening a PR.")
        return

    if not outcome["verified"]:
        print(
            "\nWARNING: no automated test verification was possible for this "
            "patch (no --test-cmd given, or dependency install failed). This "
            "result relies on ReviewAgent's judgment alone -- review the diff "
            "carefully before approving."
        )

    if not auto_approve:
        answer = input("\nFork, push, and open a real PR with this patch? [y/N] ").strip().lower()
        if answer != "y":
            print("Not opening a PR (human declined). Patch saved locally above.")
            return

    pr_result = await _open_real_pr(
        owner, name, issue_number, outcome["patch"], outcome["changed_files"], outcome["pr_draft"]
    )
    print("PR opened:", pr_result.get("html_url", pr_result))


async def cmd_resolve(issue_id: str, auto_approve: bool) -> None:
    issue = _load_issue(issue_id)
    print(f"Resolving {issue_id}: {issue['title']}\n")

    outcome = await run_for_issue(issue)

    print("=" * 60)
    print(f"Resolved: {outcome['resolved']}  (attempts: {outcome['attempts']})")
    print("-" * 60)
    print("Patch:\n", outcome["patch"])
    print("-" * 60)
    print("Review verdict:", outcome["review_verdict"])
    print("-" * 60)
    print("PR draft:\n", outcome["pr_draft"])
    print("=" * 60)

    if not outcome["resolved"]:
        print("Issue was not resolved -- not opening a PR.")
        return

    if not auto_approve:
        answer = input("\nOpen a real PR with this patch? [y/N] ").strip().lower()
        if answer != "y":
            print("Not opening a PR (human declined).")
            return

    await _open_pull_request(issue, outcome)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python3 -m agent.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve_p = sub.add_parser("resolve", help="Resolve one issue end to end")
    resolve_p.add_argument("--issue-id", required=True)
    resolve_p.add_argument(
        "--approve",
        action="store_true",
        help="Skip the interactive confirmation and open the PR automatically "
        "(NOT recommended -- defeats the human-in-the-loop safety gate; only "
        "for scripted/CI use where you've reviewed the risk).",
    )

    try_p = sub.add_parser(
        "try-real-issue", help="Attempt a real GitHub issue (weaker verification, see README)"
    )
    try_p.add_argument("--repo", required=True, help="owner/name")
    try_p.add_argument("--issue", type=int, required=True, dest="issue_number")
    try_p.add_argument(
        "--test-cmd",
        default=None,
        help="A pytest invocation to run before/after as a regression check, "
        "e.g. 'pytest -v'. If omitted, no automated verification is possible "
        "and the result relies on ReviewAgent's judgment alone.",
    )
    try_p.add_argument(
        "--target-test",
        default=None,
        help="A specific test node id (e.g. tests/test_x.py::test_y) that "
        "should flip from failing to passing. If omitted, any newly-passing "
        "test counts as evidence the fix worked.",
    )
    try_p.add_argument("--max-attempts", type=int, default=2)
    try_p.add_argument(
        "--approve",
        action="store_true",
        help="Skip the interactive confirmation and fork/push/open the PR "
        "automatically (NOT recommended -- defeats the human-in-the-loop "
        "safety gate; only for scripted use where you've reviewed the risk).",
    )

    args = parser.parse_args()
    if args.command == "resolve":
        asyncio.run(cmd_resolve(args.issue_id, args.approve))
    elif args.command == "try-real-issue":
        asyncio.run(
            cmd_try_real_issue(
                args.repo,
                args.issue_number,
                args.test_cmd,
                args.target_test,
                args.max_attempts,
                args.approve,
            )
        )


if __name__ == "__main__":
    main()
