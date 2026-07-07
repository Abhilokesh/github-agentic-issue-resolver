"""Best-effort dependency install for an arbitrary cloned repo, so its own
test suite has a chance of actually running.

Security note: installing a repo's dependencies (`pip install -e .` or
`-r requirements.txt`) can execute arbitrary code from that repo's
setup.py/build backend -- this is a strictly higher-risk step than
anything else in this project, since until now every sandboxed execution
was against code we authored ourselves (the seeded benchmark repo) or a
patch we're explicitly reviewing. There's no way to "fix" this and still
run someone else's test suite; the mitigation is running it under the
same resource/timeout/scrubbed-env limits as everything else (see
subprocess_safety.py), not skipping it silently.
"""

from __future__ import annotations

import subprocess
import venv
from pathlib import Path

from .subprocess_safety import limit_resources, scrubbed_env

_INSTALL_TIMEOUT_SECONDS = 180


def prepare_test_env(repo_root: Path) -> tuple[Path, str | None]:
    """Create a venv inside `repo_root` and best-effort install deps.

    Returns (python_bin, install_error). install_error is None on success
    (or if there was nothing to install); callers should surface it rather
    than assume the test suite will actually run if it's set.
    """
    venv_dir = repo_root / ".agent_venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python_bin = venv_dir / "bin" / "python"

    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        result = subprocess.run(
            [str(python_bin), "-m", "pip", "install", "-e", "."],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=_INSTALL_TIMEOUT_SECONDS,
            env=scrubbed_env(extra_allowlist=("PIP_CACHE_DIR",)),
            preexec_fn=limit_resources,
        )
        if result.returncode == 0:
            return python_bin, None
        install_error = result.stderr[-2000:]
    else:
        install_error = None

    req_file = repo_root / "requirements.txt"
    if req_file.exists():
        result = subprocess.run(
            [str(python_bin), "-m", "pip", "install", "-r", str(req_file)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=_INSTALL_TIMEOUT_SECONDS,
            env=scrubbed_env(extra_allowlist=("PIP_CACHE_DIR",)),
            preexec_fn=limit_resources,
        )
        if result.returncode == 0:
            return python_bin, None
        install_error = result.stderr[-2000:]

    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "pytest"],
        capture_output=True,
        text=True,
        timeout=_INSTALL_TIMEOUT_SECONDS,
    )
    return python_bin, install_error
