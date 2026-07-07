"""Demo-mode CLI: resolve one issue through the full pipeline, then --
only after an explicit human confirmation -- push a branch and open a
real PR against SANDBOX_REPO via the GitHub MCP server.

    python3 -m agent.cli resolve --issue-id B1

This is deliberately separate from benchmark/run_benchmark.py, which
never touches GitHub at all.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

from .coordinator import run_for_issue  # noqa: E402
from .tools.github_mcp import build_github_toolset  # noqa: E402

ISSUES_YAML = REPO_ROOT / "sandbox_repo" / "issues.yaml"


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

    args = parser.parse_args()
    if args.command == "resolve":
        asyncio.run(cmd_resolve(args.issue_id, args.approve))


if __name__ == "__main__":
    main()
