"""Helpers for validating and inspecting unified diffs before they touch
the sandbox. Kept separate from sandbox_exec so the parsing logic can be
unit-tested without spinning up a subprocess.
"""

from __future__ import annotations

import re

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.MULTILINE)
_PLUSPLUSPLUS_RE = re.compile(r"^\+\+\+ b/(\S+)", re.MULTILINE)
_IMPORT_RE = re.compile(r"^\+\s*(?:import|from)\s+([\w]+)")

DEPENDENCY_FILES = {"requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"}


class InvalidPatchError(ValueError):
    pass


_FENCE_RE = re.compile(r"^```(?:diff|patch)?\n|\n```$", re.MULTILINE)


def normalize_patch_text(patch_text: str) -> str:
    """Defensively clean up common LLM diff-output quirks: markdown code
    fences the model added despite instructions not to, and a missing
    trailing newline (which makes `git apply` treat the patch as corrupt).
    """
    text = _FENCE_RE.sub("", patch_text.strip())
    if not text.endswith("\n"):
        text += "\n"
    return text


def validate_unified_diff(patch_text: str) -> None:
    """Raise InvalidPatchError if `patch_text` doesn't look like a unified diff."""
    if not patch_text.strip():
        raise InvalidPatchError("Patch is empty.")
    if "--- " not in patch_text or "+++ " not in patch_text:
        raise InvalidPatchError(
            "Patch doesn't contain '---'/'+++' file headers -- not a unified diff."
        )


def changed_files(patch_text: str) -> list[str]:
    """Return the list of file paths touched by `patch_text`."""
    files = _DIFF_HEADER_RE.findall(patch_text)
    if files:
        return sorted({b for _, b in files})
    return sorted(set(_PLUSPLUSPLUS_RE.findall(patch_text)))


def added_import_modules(patch_text: str) -> list[str]:
    """Return top-level module names introduced by newly added import lines."""
    modules = set()
    for line in patch_text.splitlines():
        if line.startswith("+++"):
            continue
        m = _IMPORT_RE.match(line)
        if m:
            modules.add(m.group(1))
    return sorted(modules)
