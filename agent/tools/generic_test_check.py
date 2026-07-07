"""Regression check for the real-issue dry-run path: run the target repo's
own test suite before and after a candidate patch, and require that
nothing which was passing starts failing. This is a weaker signal than
the benchmark's precise oracle_cmd-per-issue design (see
agent/dry_run_workflow.py's docstring) -- it proves "didn't break
anything else," not "definitely fixed the described bug."

Assumes a pytest-based test command (documented limitation, matches the
rest of this project) -- a genuinely universal multi-framework test
result parser is a separate, much bigger problem.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .subprocess_safety import limit_resources, scrubbed_env

_TEST_LINE_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR)\b")
_TIMEOUT_SECONDS = 120


def parse_pytest_verbose_output(stdout: str) -> dict[str, str]:
    """Pure parsing logic, split out so it's unit-testable without running
    a real subprocess. Extracts `path::test PASSED|FAILED|ERROR` lines from
    `pytest -v` output."""
    results: dict[str, str] = {}
    for line in stdout.splitlines():
        m = _TEST_LINE_RE.match(line)
        if m:
            results[m.group(1)] = m.group(2)
    return results


def run_tests_and_parse(
    python_bin: Path, repo_root: Path, test_cmd: str, timeout: int = _TIMEOUT_SECONDS
) -> dict[str, str]:
    """Run `test_cmd` (a pytest invocation) in `repo_root` using `python_bin`,
    and parse verbose per-test PASSED/FAILED/ERROR results.

    Returns {test_node_id: "PASSED"|"FAILED"|"ERROR"}. Forces `-v` onto the
    command if not already present, since the parser needs per-test lines.
    """
    cmd = test_cmd if " -v" in test_cmd or test_cmd.endswith("-v") else f"{test_cmd} -v"
    # Run through the venv's python -m pytest rather than a bare `pytest`
    # so it resolves to the venv's installed packages.
    full_cmd = cmd.replace("pytest", f"{python_bin} -m pytest", 1)

    result = subprocess.run(
        full_cmd,
        shell=True,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=scrubbed_env(),
        preexec_fn=limit_resources,
    )
    return parse_pytest_verbose_output(result.stdout)


def diff_test_results(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    """Compare before/after per-test results.

    regressions: tests that were PASSED before and are no longer PASSED.
    newly_fixed: tests that were not PASSED before and are PASSED now.
    """
    regressions = [
        test_id
        for test_id, status in before.items()
        if status == "PASSED" and after.get(test_id) != "PASSED"
    ]
    newly_fixed = [
        test_id
        for test_id, status in before.items()
        if status != "PASSED" and after.get(test_id) == "PASSED"
    ]
    # Tests that only exist in `after` (newly added by the patch) also count
    # as newly fixed if they pass.
    newly_fixed += [
        test_id
        for test_id, status in after.items()
        if test_id not in before and status == "PASSED"
    ]
    return {"regressions": regressions, "newly_fixed": newly_fixed}
