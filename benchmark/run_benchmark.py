"""Runs the full multi-agent pipeline (Triage -> Code/Test/Review loop ->
PR draft) against every issue in sandbox_repo/issues.yaml and records
pass/fail + timing/attempts for each. No real GitHub calls are made here
-- this is the fast, free, local benchmark; PR creation only happens in
demo mode (agent/cli.py).

Usage: python3 benchmark/run_benchmark.py [issue_id ...]
  (with no args, runs the full issue set)
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT))

from agent.coordinator import run_for_issue  # noqa: E402

ISSUES_YAML = REPO_ROOT / "sandbox_repo" / "issues.yaml"
RESULTS_PATH = REPO_ROOT / "benchmark" / "results" / "multi_agent.json"


async def run_all(issue_ids: list[str] | None = None) -> list[dict]:
    issues = yaml.safe_load(ISSUES_YAML.read_text())["issues"]
    if issue_ids:
        issues = [i for i in issues if i["id"] in issue_ids]

    results = []
    for issue in issues:
        print(f"--- Resolving {issue['id']}: {issue['title']} ---", flush=True)
        start = time.perf_counter()
        outcome = await run_for_issue(issue)
        elapsed = time.perf_counter() - start

        record = {
            "issue_id": issue["id"],
            "category": issue["category"],
            "resolved": outcome["resolved"],
            "attempts": outcome["attempts"],
            "elapsed_seconds": round(elapsed, 1),
            "review_verdict": outcome["review_verdict"],
        }
        results.append(record)
        status = "RESOLVED" if record["resolved"] else "FAILED"
        print(
            f"    {status} in {record['attempts']} attempt(s), "
            f"{record['elapsed_seconds']}s",
            flush=True,
        )
    return results


def main() -> None:
    issue_ids = sys.argv[1:] or None
    results = asyncio.run(run_all(issue_ids))

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    resolved = sum(1 for r in results if r["resolved"])
    print(f"\n{resolved}/{len(results)} issues resolved. Results -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
