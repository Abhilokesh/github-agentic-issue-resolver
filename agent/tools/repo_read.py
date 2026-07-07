"""Read-only access to the pristine seeded repo, for the CodingAgent to
inspect real file content before writing a diff -- never let the model
guess/hallucinate what a file currently contains.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_REPO = (REPO_ROOT / "sandbox_repo").resolve()


def read_repo_file(path: str) -> str:
    """Read the current content of a file in the sandbox repo.

    Args:
      path: file path relative to the repo root, e.g. "stringkit/text.py".

    Returns:
      The file's text content, or an "Error: ..." message if the path is
      invalid or outside the repo.
    """
    target = (SANDBOX_REPO / path).resolve()
    if target != SANDBOX_REPO and SANDBOX_REPO not in target.parents:
        return "Error: path escapes the repo root, not allowed."
    if not target.exists():
        return f"Error: {path} does not exist."
    if not target.is_file():
        return f"Error: {path} is not a file."
    return target.read_text()
