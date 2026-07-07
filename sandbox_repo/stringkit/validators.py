"""Simple format validators."""

import re
import sys

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://[^\s]+$")


def is_valid_email(s: str) -> bool:
    """Return True if `s` looks like a valid email address."""
    return bool(_EMAIL_RE.match(s))


def is_valid_url(s):
    """Return True if `s` looks like a valid http(s) URL."""
    return bool(_URL_RE.match(s))
