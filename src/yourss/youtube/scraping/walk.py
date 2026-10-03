"""Generic helpers to search a decoded JSON payload, whatever its nesting."""

from collections.abc import Iterator
from typing import Any


def iter_key[T](key: str, payload: Any, cls: type[T] | None = None) -> Iterator[T]:
    """
    Recursively yield every value stored under ``key`` anywhere in ``payload``
    (the equivalent of a ``$..key`` jsonpath descent), optionally filtered by
    type. Traversal is depth-first; a matching value is yielded before its own
    children are explored.
    """
    if isinstance(payload, dict):
        for k, value in payload.items():
            if k == key and value is not None and (cls is None or isinstance(value, cls)):
                yield value
            yield from iter_key(key, value, cls)
    elif isinstance(payload, list):
        for item in payload:
            yield from iter_key(key, item, cls)


def find_key[T](key: str, payload: Any, cls: type[T] | None = None) -> T | None:
    """First value found under ``key`` anywhere in ``payload``, else ``None``."""
    return next(iter_key(key, payload, cls), None)
