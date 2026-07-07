"""Ephemeral sandbox: apply a candidate patch to a throwaway copy of a repo
and run an oracle command against it.

Security note (documented limitation, not hidden): see
agent/tools/subprocess_safety.py for the isolation this provides and its
limits.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .patch_tools import InvalidPatchError, normalize_patch_text, validate_unified_diff
from .slopsquatting_guard import check_no_new_dependencies
from .subprocess_safety import limit_resources, scrubbed_env

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_REPO = REPO_ROOT / "sandbox_repo"

_TIMEOUT_SECONDS = 30


def run_in_sandbox(patch: str, oracle_cmd: str, repo_root: Path = SANDBOX_REPO) -> dict:
    """Apply `patch` (a unified diff) to a fresh copy of `repo_root` and run
    `oracle_cmd` against it.

    Args:
      patch: unified diff text (e.g. `git diff` output) to apply.
      oracle_cmd: shell command to run from the repo root; exit code 0
        means the issue is considered resolved.
      repo_root: the repo to copy and patch. Defaults to the seeded
        sandbox repo; the real-issue dry-run path passes a cloned repo.

    Returns:
      A dict with keys: guard_passed, guard_reason, applied, apply_error,
      oracle_passed, returncode, stdout, stderr.
    """
    patch = normalize_patch_text(patch)
    ok, reason = check_no_new_dependencies(patch)
    if not ok:
        return {
            "guard_passed": False,
            "guard_reason": reason,
            "applied": False,
            "apply_error": None,
            "oracle_passed": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
        }

    try:
        validate_unified_diff(patch)
    except InvalidPatchError as e:
        return {
            "guard_passed": True,
            "guard_reason": "",
            "applied": False,
            "apply_error": str(e),
            "oracle_passed": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
        }

    work_dir = Path(tempfile.mkdtemp(prefix="agent_sandbox_"))
    try:
        shutil.copytree(repo_root, work_dir, dirs_exist_ok=True)

        patch_file = work_dir / "_candidate.patch"
        patch_file.write_text(patch)
        apply_result = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", str(patch_file)],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
        patch_file.unlink(missing_ok=True)

        if apply_result.returncode != 0:
            return {
                "guard_passed": True,
                "guard_reason": "",
                "applied": False,
                "apply_error": apply_result.stderr.strip(),
                "oracle_passed": False,
                "returncode": None,
                "stdout": "",
                "stderr": "",
            }

        oracle_result = subprocess.run(
            oracle_cmd,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            env=scrubbed_env(),
            preexec_fn=limit_resources,
        )
        return {
            "guard_passed": True,
            "guard_reason": "",
            "applied": True,
            "apply_error": None,
            "oracle_passed": oracle_result.returncode == 0,
            "returncode": oracle_result.returncode,
            "stdout": oracle_result.stdout[-4000:],
            "stderr": oracle_result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as e:
        return {
            "guard_passed": True,
            "guard_reason": "",
            "applied": True,
            "apply_error": None,
            "oracle_passed": False,
            "returncode": None,
            "stdout": (e.stdout or "")[-4000:] if isinstance(e.stdout, str) else "",
            "stderr": f"Timed out after {_TIMEOUT_SECONDS}s running oracle_cmd.",
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
