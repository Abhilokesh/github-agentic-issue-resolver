"""Ephemeral sandbox: apply a candidate patch to a throwaway copy of the
seeded repo and run an oracle command against it.

Security note (documented limitation, not hidden): this isolates via a
fresh temp directory, a resource-limited/timeout-bounded subprocess, and
a scrubbed environment (no secrets passed through) -- but NOT via a
container or network namespace, since this dev environment has no
Docker. A patch's test/oracle run could still make outbound network
calls. Hardening path for production use: run this same subprocess
inside a container (Docker/gVisor) with networking disabled.
"""

from __future__ import annotations

import resource
import shutil
import subprocess
import tempfile
from pathlib import Path

from .patch_tools import InvalidPatchError, normalize_patch_text, validate_unified_diff
from .slopsquatting_guard import check_no_new_dependencies

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_REPO = REPO_ROOT / "sandbox_repo"

_CPU_SECONDS_LIMIT = 20
_ADDRESS_SPACE_LIMIT_BYTES = 512 * 1024 * 1024  # 512 MB
_TIMEOUT_SECONDS = 30

# Deliberately excludes GEMINI_API_KEY / GITHUB_PERSONAL_ACCESS_TOKEN /
# anything else from the real environment -- the sandboxed process only
# gets what it needs to run pytest/ruff.
_SANDBOX_ENV_ALLOWLIST = ("PATH", "VIRTUAL_ENV", "LANG", "LC_ALL", "HOME")


def _limit_resources() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (_CPU_SECONDS_LIMIT, _CPU_SECONDS_LIMIT))
    resource.setrlimit(
        resource.RLIMIT_AS, (_ADDRESS_SPACE_LIMIT_BYTES, _ADDRESS_SPACE_LIMIT_BYTES)
    )


def _scrubbed_env() -> dict[str, str]:
    import os

    return {k: v for k, v in os.environ.items() if k in _SANDBOX_ENV_ALLOWLIST}


def run_in_sandbox(patch: str, oracle_cmd: str) -> dict:
    """Apply `patch` (a unified diff) to a fresh copy of the sandbox repo
    and run `oracle_cmd` against it.

    Args:
      patch: unified diff text (e.g. `git diff` output) to apply.
      oracle_cmd: shell command to run from the repo root; exit code 0
        means the issue is considered resolved.

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
        shutil.copytree(SANDBOX_REPO, work_dir, dirs_exist_ok=True)

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
            env=_scrubbed_env(),
            preexec_fn=_limit_resources,
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
