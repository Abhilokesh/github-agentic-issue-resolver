"""Checks that specific public functions are fully type-annotated.

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
