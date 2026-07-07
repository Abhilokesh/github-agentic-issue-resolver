"""Deterministically (re)generates sandbox_repo/: a small Python package
("stringkit") with 10 intentionally seeded issues across 5 categories,
plus its own git history. Safe to re-run — wipes and rebuilds sandbox_repo/.

Usage: python3 scripts/seed_sandbox_repo.py

IMPORTANT: the seeded-bug annotations below exist only as comments in
*this* generator script, never inside the FILES dict values. FILES values
become sandbox_repo/ source the agent under test reads and solves against
-- if the answer were spelled out in an inline comment there, the
benchmark would be trivially gameable and the multi-agent-vs-baseline
comparison would be meaningless. The answer key lives here and in
issues.yaml's `category`/`oracle_cmd` fields, both outside sandbox_repo/.

Seed map (issue id -> what's actually wrong):
  A1 (doctest)      casing.py:to_snake_case   -- regex leaves a stray
                                                  trailing "_" and misses
                                                  the last capital split,
                                                  so its own doctest fails.
  A2 (doctest)      text.py:truncate          -- code is correct; the
                                                  docstring's example
                                                  output has an extra
                                                  "." typo'd into it.
  B1 (lint)         validators.py             -- unused `import sys`
                                                  (ruff F401).
  B2 (lint)         formatting.py:pluralize   -- mutable default arg
                                                  `exceptions=[]` (ruff
                                                  B006).
  C1 (type hints)   text.py:word_count        -- no annotations at all.
  C2 (type hints)   validators.py:is_valid_url -- missing `-> bool`.
  D1 (outdated API) formatting.py:generated_at_label -- datetime.utcnow()
                                                  is deprecated (3.12+);
                                                  pytest.ini errors on it.
  D2 (outdated API) formatting.py              -- `from typing import
                                                  List` instead of builtin
                                                  `list` (ruff UP035).
  E1 (missing test) formatting.py:human_readable_size / pluralize
                                                  -- larger-unit branches
                                                  and pluralize() are
                                                  completely untested.
  E2 (missing test) validators.py:is_valid_url -- completely untested.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = ROOT / "sandbox_repo"

FILES: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Package source (with seeded issues)
# ---------------------------------------------------------------------------

FILES["stringkit/__init__.py"] = '''"""stringkit: small text-utility library used as the agent benchmark sandbox."""

from .casing import to_snake_case, to_camel_case
from .slug import slugify
from .text import truncate, word_count
from .validators import is_valid_email, is_valid_url
from .formatting import human_readable_size, pluralize

__all__ = [
    "to_snake_case",
    "to_camel_case",
    "slugify",
    "truncate",
    "word_count",
    "is_valid_email",
    "is_valid_url",
    "human_readable_size",
    "pluralize",
]
'''

# --- Category A: doctest / documentation accuracy -------------------------
# A1: casing.to_snake_case has a real bug that makes its own doctest fail.
# A2: text.truncate's docstring example shows the wrong expected output.

FILES["stringkit/casing.py"] = '''"""Case-conversion helpers."""

import re


def to_snake_case(name: str) -> str:
    """Convert a CamelCase or PascalCase string to snake_case.

    >>> to_snake_case("HelloWorld")
    \'hello_world\'
    >>> to_snake_case("already_snake")
    \'already_snake\'
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\\1_\\2", name)
    return s1.lower() + "_"


def to_camel_case(name: str) -> str:
    """Convert a snake_case string to camelCase.

    >>> to_camel_case("hello_world")
    \'helloWorld\'
    """
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])
'''

FILES["stringkit/slug.py"] = '''"""Slug generation helpers."""

import re


def slugify(text: str, separator: str = "-") -> str:
    """Convert text into a URL-friendly slug.

    >>> slugify("Hello, World!")
    'hello-world'
    >>> slugify("  Multiple   spaces  ")
    'multiple-spaces'
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\\s-]", "", text)
    text = re.sub(r"[\\s-]+", separator, text)
    return text.strip(separator)
'''

FILES["stringkit/text.py"] = '''"""Text manipulation helpers."""


def truncate(text: str, length: int = 80, suffix: str = "...") -> str:
    """Truncate text to at most `length` characters, appending `suffix`.

    >>> truncate("Hello there", length=4, suffix="")
    'Hell!'
    """
    if len(text) <= length:
        return text
    return text[:length] + suffix


def word_count(text):
    """Count the number of whitespace-separated words in `text`."""
    return len(text.split())
'''

FILES["stringkit/validators.py"] = '''"""Simple format validators."""

import re
import sys

_EMAIL_RE = re.compile(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")
_URL_RE = re.compile(r"^https?://[^\\s]+$")


def is_valid_email(s: str) -> bool:
    """Return True if `s` looks like a valid email address."""
    return bool(_EMAIL_RE.match(s))


def is_valid_url(s):
    """Return True if `s` looks like a valid http(s) URL."""
    return bool(_URL_RE.match(s))
'''

FILES["stringkit/formatting.py"] = '''"""Number/size formatting helpers."""

from datetime import datetime
from typing import List


def human_readable_size(num_bytes: float) -> str:
    """Convert a byte count into a human-readable string, e.g. '1.5 KB'."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def pluralize(word: str, count: int, exceptions=[]):
    """Return `word` pluralized (naive 's' suffix) unless count == 1."""
    for singular, plural in exceptions:
        if word == singular:
            return word if count == 1 else plural
    return word if count == 1 else word + "s"


def generated_at_label() -> str:
    """Return a human-readable UTC timestamp label for generated reports."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def build_report_lines(entries: List[str]) -> List[str]:
    """Return `entries` prefixed with a bullet point."""
    return [f"- {entry}" for entry in entries]
'''

# ---------------------------------------------------------------------------
# Tests (pytest + pytest-bdd for the behavioral/doctest categories)
# ---------------------------------------------------------------------------

FILES["conftest.py"] = "# Empty: presence at repo root makes pytest add this dir to sys.path.\n"

FILES["tests/__init__.py"] = ""

FILES["tests/test_slug.py"] = '''from stringkit.slug import slugify


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_custom_separator():
    assert slugify("Hello World", separator="_") == "hello_world"
'''

FILES["tests/test_formatting.py"] = '''from stringkit.formatting import (
    human_readable_size,
    build_report_lines,
    generated_at_label,
)


def test_human_readable_size_bytes():
    assert human_readable_size(500) == "500.0 B"


def test_human_readable_size_kb():
    assert human_readable_size(2048) == "2.0 KB"


def test_build_report_lines():
    assert build_report_lines(["a", "b"]) == ["- a", "- b"]


def test_generated_at_label_no_deprecation_warning():
    # pytest.ini turns DeprecationWarning from stringkit.formatting into
    # an error, so this raises until the function stops using a
    # deprecated datetime API.
    generated_at_label()
'''

FILES["tests/test_validators.py"] = '''from stringkit.validators import is_valid_email


def test_is_valid_email_true():
    assert is_valid_email("user@example.com") is True


def test_is_valid_email_false():
    assert is_valid_email("not-an-email") is False
'''

FILES["tests/test_type_hints.py"] = '''"""Checks that specific public functions are fully type-annotated.

Kept isolated (introspection, not a whole-package type checker) so each
check is independent of unrelated modules' annotation state.
"""

import inspect

from stringkit.text import word_count
from stringkit.validators import is_valid_url


def _fully_annotated(fn) -> bool:
    sig = inspect.signature(fn)
    if sig.return_annotation is inspect.Signature.empty:
        return False
    return all(
        p.annotation is not inspect.Signature.empty
        for p in sig.parameters.values()
    )


def test_word_count_has_type_hints():
    assert _fully_annotated(word_count)


def test_is_valid_url_has_type_hints():
    assert _fully_annotated(is_valid_url)
'''

FILES["tests/test_casing.py"] = '''from stringkit.casing import to_camel_case


def test_to_camel_case():
    assert to_camel_case("hello_world") == "helloWorld"
'''

FILES["features/formatting.feature"] = """Feature: Formatting helpers behavior
  As a developer using stringkit
  I want human_readable_size and pluralize fully specified by tests
  So that their behavior is guaranteed not to regress

  Scenario: Format a byte count in the megabyte range
    Given a byte count of 1500000
    When I format it as a human readable size
    Then the result is "1.4 MB"

  Scenario: Pluralize a regular word
    Given the word "cat" with count 2
    When I pluralize it
    Then the result is "cats"

  Scenario: Do not pluralize a singular count
    Given the word "cat" with count 1
    When I pluralize it
    Then the result is "cat"
"""

FILES["features/url_validation.feature"] = """Feature: URL validation behavior

  Scenario: Recognize a valid https URL
    Given the string "https://example.com"
    When I validate it as a URL
    Then it is considered valid

  Scenario: Reject a string that is not a URL
    Given the string "not a url"
    When I validate it as a URL
    Then it is considered invalid
"""

FILES["pytest.ini"] = """[pytest]
testpaths = tests
filterwarnings =
    error::DeprecationWarning:stringkit.formatting
"""

FILES["requirements.txt"] = """pytest>=8.2.0
pytest-bdd>=7.2.0
ruff>=0.6.0
"""

FILES["README.md"] = """# stringkit

A small collection of text-utility helpers: case conversion, slugs,
truncation/word counting, email/URL validation, and human-readable
formatting.

    pip install -e .
    pytest
"""

FILES["issues.yaml"] = '''# Curated benchmark issue set. Each issue's `description` is what gets
# fed to the agent as "the GitHub issue" -- everything else here
# (category, oracle_cmd) is benchmark-harness metadata the agent never
# sees directly. oracle_cmd is a shell command run from the repo root;
# exit code 0 means the issue is resolved.

issues:
  - id: A1
    title: "to_snake_case doesn't match its own documented example"
    category: documentation
    description: |
      I ran the example from the docstring of `to_snake_case` and it
      doesn't match what's documented:

          >>> to_snake_case("HelloWorld")

      The docstring says this should return 'hello_world', but that's
      not what I'm getting. Please make the function and its documented
      example consistent, so the doctest passes.
    oracle_cmd: "pytest --doctest-modules stringkit/casing.py -q"
    target_hint: stringkit/casing.py
    context_files: [stringkit/casing.py]

  - id: A2
    title: "truncate() docstring example looks wrong"
    category: documentation
    description: |
      The docstring example for `truncate()` doesn't look right:

          >>> truncate("Hello there", length=4, suffix="")

      Can you check whether the function or the documented example
      output is correct, and fix whichever one is wrong so the doctest
      passes?
    oracle_cmd: "pytest --doctest-modules stringkit/text.py -q"
    target_hint: stringkit/text.py
    context_files: [stringkit/text.py]

  - id: B1
    title: "Unused import in validators.py"
    category: lint
    description: |
      `ruff check stringkit/validators.py` reports an unused import.
      Please clean it up.
    oracle_cmd: "ruff check --select F401 stringkit/validators.py"
    target_hint: stringkit/validators.py
    context_files: [stringkit/validators.py]

  - id: B2
    title: "pluralize() uses a mutable default argument"
    category: lint
    description: |
      `ruff` flags `pluralize()`'s `exceptions=[]` default argument as a
      mutable-default-argument antipattern. Please fix this without
      changing the function's existing behavior.
    oracle_cmd: "ruff check --select B stringkit/formatting.py"
    target_hint: stringkit/formatting.py
    context_files: [stringkit/formatting.py]

  - id: C1
    title: "word_count() has no type hints"
    category: type-hints
    description: |
      Every other public function in stringkit has full type
      annotations except `word_count()`. Please add appropriate
      parameter and return type annotations.
    oracle_cmd: "pytest tests/test_type_hints.py::test_word_count_has_type_hints -q"
    target_hint: stringkit/text.py
    context_files: [stringkit/text.py]

  - id: C2
    title: "is_valid_url() is missing type annotations"
    category: type-hints
    description: |
      `is_valid_url()` takes a string and returns a bool but has no type
      annotations at all. Please add the missing type hints.
    oracle_cmd: "pytest tests/test_type_hints.py::test_is_valid_url_has_type_hints -q"
    target_hint: stringkit/validators.py
    context_files: [stringkit/validators.py]

  - id: D1
    title: "DeprecationWarning from generated_at_label() on Python 3.12+"
    category: outdated-api
    description: |
      Running the test suite on Python 3.12 raises a DeprecationWarning
      pointing at `generated_at_label()`. Please update it to use a
      non-deprecated datetime API while keeping the same output format.
    oracle_cmd: "pytest tests/test_formatting.py::test_generated_at_label_no_deprecation_warning -q"
    target_hint: stringkit/formatting.py
    context_files: [stringkit/formatting.py]

  - id: D2
    title: "formatting.py uses typing.List instead of the builtin generic"
    category: outdated-api
    description: |
      `ruff` flags `formatting.py` for using `typing.List` instead of
      the modern builtin `list[...]` generic syntax. Please modernize
      it.
    oracle_cmd: "ruff check --select UP stringkit/formatting.py"
    target_hint: stringkit/formatting.py
    context_files: [stringkit/formatting.py]

  - id: E1
    title: "human_readable_size and pluralize are missing tests"
    category: missing-tests
    description: |
      `human_readable_size`'s larger-unit branches (MB and up) and
      `pluralize()` have no test coverage at all. A Gherkin spec for the
      required scenarios already exists at
      `features/formatting.feature` -- please implement pytest-bdd step
      definitions in `tests/step_defs/test_formatting_bdd.py` that
      satisfy it.
    oracle_cmd: "pytest tests/step_defs/test_formatting_bdd.py -q"
    target_hint: features/formatting.feature
    context_files: [features/formatting.feature, stringkit/formatting.py]

  - id: E2
    title: "is_valid_url has no tests"
    category: missing-tests
    description: |
      `is_valid_url()` has no test coverage. A Gherkin spec for the
      required scenarios already exists at
      `features/url_validation.feature` -- please implement pytest-bdd
      step definitions in `tests/step_defs/test_url_validation_bdd.py`
      that satisfy it.
    oracle_cmd: "pytest tests/step_defs/test_url_validation_bdd.py -q"
    target_hint: features/url_validation.feature
    context_files: [features/url_validation.feature, stringkit/validators.py]
'''

FILES[".gitignore"] = """__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
"""


def main() -> None:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)

    for rel_path, content in FILES.items():
        path = SANDBOX / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    # No git init here: sandbox_exec.py applies patches with plain `git
    # apply`, which works fine against a bare directory (verified) and
    # doesn't need sandbox_repo/ to be its own repo. Keeping it as plain
    # files avoids it being tracked as a broken nested-repo/submodule
    # reference when this project itself is committed to git.
    print(f"sandbox_repo seeded at {SANDBOX}")


if __name__ == "__main__":
    main()
