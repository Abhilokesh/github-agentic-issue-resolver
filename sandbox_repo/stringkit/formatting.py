"""Number/size formatting helpers."""

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
