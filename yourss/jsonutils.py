from typing import Dict, Iterator, Type, TypeVar

from jsonpath_ng import parse

T = TypeVar("T")


def json_iter(path: str, payload: Dict, cls: Type[T] | None = None) -> Iterator[T]:
    for match in parse(path).find(payload):
        out = match.value
        if out is not None and (cls is None or isinstance(out, cls)):
            yield out


def json_first(path: str, payload: Dict, cls: Type[T] | None = None) -> T:
    return next(json_iter(path, payload, cls=cls))
