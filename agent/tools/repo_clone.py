"""Read-only clone of an arbitrary public GitHub repo, for the real-issue
dry-run path. Always HTTPS + no auth -- cloning never needs write access
regardless of what the rest of that pipeline does with a PAT.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_CLONE_TIMEOUT_SECONDS = 120


def clone_repo(owner: str, repo: str, dest: Path) -> None:
    """Shallow-clone https://github.com/{owner}/{repo} into `dest`.

    Raises subprocess.CalledProcessError if the clone fails (private repo,
    doesn't exist, network error, etc.) -- callers should let this surface
    rather than silently continuing with a missing/partial clone.
    """
    url = f"https://github.com/{owner}/{repo}.git"
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
        timeout=_CLONE_TIMEOUT_SECONDS,
    )
