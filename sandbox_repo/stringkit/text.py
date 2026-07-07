"""Text manipulation helpers."""


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
