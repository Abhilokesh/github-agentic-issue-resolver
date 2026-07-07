"""Shared subprocess isolation helpers: resource/timeout limits and a
scrubbed environment. Used by both sandbox_exec.py (the seeded benchmark
repo) and generic_test_check.py (arbitrary cloned repos) -- the latter is
if anything a *higher*-risk surface (unfamiliar code, unfamiliar test
suite), so it gets the same protections, not weaker ones.

Documented limitation, not hidden: this isolates via a fresh temp
directory, a resource-limited/timeout-bounded subprocess, and a scrubbed
environment (no secrets passed through) -- but NOT via a container or
network namespace, since this dev environment has no Docker. A
sandboxed process could still make outbound network calls. Hardening
path for production use: run this same subprocess inside a container
(Docker/gVisor) with networking disabled.
"""

from __future__ import annotations

import os
import resource

CPU_SECONDS_LIMIT = 20
ADDRESS_SPACE_LIMIT_BYTES = 512 * 1024 * 1024  # 512 MB

# Deliberately excludes GEMINI_API_KEY / GITHUB_PERSONAL_ACCESS_TOKEN /
# anything else from the real environment -- the sandboxed process only
# gets what it needs to run pytest/ruff/pip.
SANDBOX_ENV_ALLOWLIST = ("PATH", "VIRTUAL_ENV", "LANG", "LC_ALL", "HOME")


def limit_resources() -> None:
    """Pass as `preexec_fn` to subprocess.run to cap CPU/memory."""
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS_LIMIT, CPU_SECONDS_LIMIT))
    resource.setrlimit(
        resource.RLIMIT_AS, (ADDRESS_SPACE_LIMIT_BYTES, ADDRESS_SPACE_LIMIT_BYTES)
    )


def scrubbed_env(extra_allowlist: tuple[str, ...] = ()) -> dict[str, str]:
    """A minimal env dict for a sandboxed subprocess -- no secrets."""
    allowlist = SANDBOX_ENV_ALLOWLIST + extra_allowlist
    return {k: v for k, v in os.environ.items() if k in allowlist}
