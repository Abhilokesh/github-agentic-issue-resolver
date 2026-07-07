"""Rejects any patch that introduces a new dependency.

None of the seeded benchmark's issue categories (doc fixes, lint, type
hints, outdated-API updates, missing tests) legitimately need a new
package -- everything is solvable with what's already imported in the
repo plus the standard library. So "no new dependencies, ever" is a
hard rule here, not a heuristic that tries to guess whether a package
name is a real one or a hallucinated ("slopsquatted") one.
"""

from __future__ import annotations

import sys

from .patch_tools import DEPENDENCY_FILES, added_import_modules, changed_files

# Modules the seeded repo already relies on, in addition to the stdlib.
_ALLOWED_THIRD_PARTY = {"pytest", "pytest_bdd", "stringkit", "tests"}

_ALLOWED_MODULES = set(sys.stdlib_module_names) | _ALLOWED_THIRD_PARTY


def check_no_new_dependencies(patch_text: str) -> tuple[bool, str]:
    """Return (ok, reason). `reason` is empty when ok is True."""
    touched = changed_files(patch_text)
    dependency_edits = [f for f in touched if f.rsplit("/", 1)[-1] in DEPENDENCY_FILES]
    if dependency_edits:
        return False, f"Patch edits dependency file(s) {dependency_edits}; not allowed."

    new_modules = [m for m in added_import_modules(patch_text) if m not in _ALLOWED_MODULES]
    if new_modules:
        return False, (
            f"Patch imports module(s) {new_modules} not already used in this repo "
            "and not in the standard library -- rejected as a potential "
            "hallucinated/unapproved dependency."
        )
    return True, ""
