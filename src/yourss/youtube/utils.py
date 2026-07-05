import re
from typing import Any, Dict, Iterator, Type, TypeVar

from glom import Path, PathAccessError, glom

T = TypeVar("T")

CHANNEL_PATTERN = r"^UC[\w-]{22}$"
PLAYLIST_PATTERN = r"^PL[\w-]{32}$"
USER_PATTERN = r"^@[\w-]+$"


def is_channel_id(text: str) -> bool:
    """
    Check if a string is a valid Youtube channel id
    """
    return bool(re.fullmatch(CHANNEL_PATTERN, text, flags=re.IGNORECASE))


def is_playlist_id(text: str) -> bool:
    """
    Check if a string is a valid Youtube playlist id
    """
    return bool(re.fullmatch(PLAYLIST_PATTERN, text, flags=re.IGNORECASE))


def is_user(text: str) -> bool:
    """
    Check if a string is a valid Youtube user
    """
    return bool(re.fullmatch(USER_PATTERN, text, flags=re.IGNORECASE))


def iter_key(key: str, payload: Any, cls: Type[T] | None = None) -> Iterator[T]:
    """
    Recursively yield every value stored under ``key`` anywhere in ``payload``
    (the equivalent of a ``$..key`` jsonpath descent), optionally filtered by
    type. Traversal is depth-first; a matching value is yielded before its own
    children are explored.
    """
    if isinstance(payload, dict):
        for k, value in payload.items():
            if (
                k == key
                and value is not None
                and (cls is None or isinstance(value, cls))
            ):
                yield value
            yield from iter_key(key, value, cls)
    elif isinstance(payload, list):
        for item in payload:
            yield from iter_key(key, item, cls)


def find_key(key: str, payload: Any, cls: Type[T] | None = None) -> T | None:
    """First value found under ``key`` anywhere in ``payload``, else ``None``."""
    return next(iter_key(key, payload, cls), None)


def find_path(path: str, payload: Any, default: Any = None) -> Any:
    """
    Read a fixed dotted ``path`` (e.g. ``"a.b.c"``) from ``payload`` via glom,
    returning ``default`` when any segment is missing.
    """
    try:
        return glom(payload, Path(*path.split(".")))
    except PathAccessError:
        return default


def filter_dict(d: Dict[str, Any], cls: Type[T]) -> Dict[str, T]:
    return {k: v for k, v in d.items() if isinstance(v, cls)}


def simple_url(url: str) -> str:
    return url.split("?", 1)[0]
