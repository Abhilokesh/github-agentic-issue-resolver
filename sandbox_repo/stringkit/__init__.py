"""stringkit: small text-utility library used as the agent benchmark sandbox."""

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
