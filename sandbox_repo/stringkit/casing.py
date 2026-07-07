"""Case-conversion helpers."""

import re


def to_snake_case(name: str) -> str:
    """Convert a CamelCase or PascalCase string to snake_case.

    >>> to_snake_case("HelloWorld")
    'hello_world'
    >>> to_snake_case("already_snake")
    'already_snake'
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return s1.lower() + "_"


def to_camel_case(name: str) -> str:
    """Convert a snake_case string to camelCase.

    >>> to_camel_case("hello_world")
    'helloWorld'
    """
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])
