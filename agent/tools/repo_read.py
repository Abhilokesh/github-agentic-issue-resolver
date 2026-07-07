"""Read-only file access for CodingAgent instances, so the model never has
to guess/hallucinate what a file currently contains before patching it.

Factory-based so the same tool shape can be bound to either the seeded
sandbox repo (the benchmark/demo path) or an arbitrary cloned repo (the
real-issue dry-run path) -- see make_read_repo_file_tool().
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_REPO = (REPO_ROOT / "sandbox_repo").resolve()


def make_read_repo_file_tool(repo_root: Path) -> Callable[[str], str]:
    """Build a `read_repo_file(path)` tool scoped to `repo_root`."""
    root = repo_root.resolve()

    def read_repo_file(path: str) -> str:
        """Read the current content of a file in the repo.

        Args:
          path: file path relative to the repo root, e.g. "stringkit/text.py".

        Returns:
          The file's text content, or an "Error: ..." message if the path is
          invalid or outside the repo.
        """
        target = (root / path).resolve()
        if target != root and root not in target.parents:
            return "Error: path escapes the repo root, not allowed."
        if not target.exists():
            return f"Error: {path} does not exist."
        if not target.is_file():
            return f"Error: {path} is not a file."
        return target.read_text()

    return read_repo_file


# Default instance used by the benchmark/demo path (agent/sub_agents/coding_agent.py).
read_repo_file = make_read_repo_file_tool(SANDBOX_REPO)
