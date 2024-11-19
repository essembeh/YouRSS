import re
from typing import Any, Dict, Iterator, Type, TypeVar

from jsonpath_ng import parse

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


def json_iter(path: str, payload: Dict, cls: Type[T] | None = None) -> Iterator[T]:
    for match in parse(path).find(payload):
        out = match.value
        if out is not None and (cls is None or isinstance(out, cls)):
            yield out


def json_first(path: str, payload: Dict, cls: Type[T] | None = None) -> T:
    return next(json_iter(path, payload, cls=cls))


def filter_dict(d: Dict[str, Any], cls: Type[T]) -> Dict[str, T]:
    return {k: v for k, v in d.items() if isinstance(v, cls)}
