"""Baseline for comparison: ONE raw Gemini call per issue, no agent
scaffolding at all (no ADK, no tools, no retry loop, no review). It gets
the same issue text and the same file contents the CodingAgent would
read via its tool, so the comparison isolates "does the multi-agent
loop help" rather than "does the baseline have less information."

Usage: python3 benchmark/baseline_single_shot.py [issue_id ...]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT))

from google import genai  # noqa: E402

from agent.tools.patch_tools import normalize_patch_text  # noqa: E402
from agent.tools.sandbox_exec import run_in_sandbox  # noqa: E402

ISSUES_YAML = REPO_ROOT / "sandbox_repo" / "issues.yaml"
SANDBOX_REPO = REPO_ROOT / "sandbox_repo"
RESULTS_PATH = REPO_ROOT / "benchmark" / "results" / "baseline_single_shot.json"
MODEL = "gemini-3.1-flash-lite"

_PROMPT_TEMPLATE = """You are fixing ONE GitHub issue in the `stringkit` Python library.

Issue: {title}

{description}

Current file content:
{file_blocks}

Respond with ONLY a valid unified diff (git diff format: `diff --git a/... \
b/...`, `---`/`+++` headers, `@@` hunks) that resolves the issue. Make the \
smallest possible change. No markdown code fences, no explanation before or \
after the diff.
"""


def _file_blocks(issue: dict) -> str:
    blocks = []
    for rel_path in issue.get("context_files", []):
        content = (SANDBOX_REPO / rel_path).read_text()
        blocks.append(f"--- {rel_path} ---\n{content}")
    return "\n\n".join(blocks)


def run_one(client: genai.Client, issue: dict) -> dict:
    prompt = _PROMPT_TEMPLATE.format(
        title=issue["title"],
        description=issue["description"],
        file_blocks=_file_blocks(issue),
    )
    start = time.perf_counter()
    response = client.models.generate_content(model=MODEL, contents=prompt)
    patch = normalize_patch_text(response.text or "")
    test_result = run_in_sandbox(patch, issue["oracle_cmd"])
    elapsed = time.perf_counter() - start

    return {
        "issue_id": issue["id"],
        "category": issue["category"],
        "resolved": bool(test_result.get("oracle_passed")),
        "elapsed_seconds": round(elapsed, 1),
        "guard_reason": test_result.get("guard_reason"),
        "apply_error": test_result.get("apply_error"),
    }


def main() -> None:
    issue_ids = sys.argv[1:] or None
    issues = yaml.safe_load(ISSUES_YAML.read_text())["issues"]
    if issue_ids:
        issues = [i for i in issues if i["id"] in issue_ids]

    client = genai.Client()
    results = []
    for issue in issues:
        print(f"--- {issue['id']}: {issue['title']} ---", flush=True)
        record = run_one(client, issue)
        results.append(record)
        print(f"    {'RESOLVED' if record['resolved'] else 'FAILED'}", flush=True)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    resolved = sum(1 for r in results if r["resolved"])
    print(f"\n{resolved}/{len(results)} issues resolved. Results -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
