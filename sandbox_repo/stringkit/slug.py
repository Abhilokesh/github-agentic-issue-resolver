"""Slug generation helpers."""

import re


def slugify(text: str, separator: str = "-") -> str:
    """Convert text into a URL-friendly slug.

    >>> slugify("Hello, World!")
    'hello-world'
    >>> slugify("  Multiple   spaces  ")
    'multiple-spaces'
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", separator, text)
    return text.strip(separator)
