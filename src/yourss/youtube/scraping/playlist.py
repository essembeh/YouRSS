"""Read a Youtube playlist page and the continuations of its list (docs/specs/playlist-tabs.md)."""

from typing import Any

from .channel import Continuation, VideoPage
from .errors import ScrapingError
from .extract import extract_client_version, extract_initial_data
from .items import parse_playlist_videos
from .walk import find_key, iter_key

# The last item of a list loads the next page; a continuation elsewhere loads suggestions, not the playlist
_CONTINUATION_ITEMS = ("continuationItemViewModel", "continuationItemRenderer")


def _next_token(last: Any) -> str | None:
    if not isinstance(last, dict) or not any(key in last for key in _CONTINUATION_ITEMS):
        return None
    # A continuation item nests a tokenless command around the one holding the token
    return next(
        (command["token"] for command in iter_key("continuationCommand", last, dict) if command.get("token")), None
    )


def _list_page(items: list[Any], client_version: str | None) -> VideoPage:
    token = _next_token(items[-1] if items else None)
    return VideoPage(
        videos=parse_playlist_videos({"items": items}),
        continuation=Continuation(token=token, client_version=client_version) if token and client_version else None,
    )


def parse_playlist_page(html: str) -> VideoPage:
    """The first page of the list of a playlist (100 videos at most), from the HTML of its Youtube page."""
    data = extract_initial_data(html)
    section = find_key("itemSectionRenderer", data, dict)
    if section is None:
        raise ScrapingError("Cannot find the list of the playlist in the Youtube page")
    return _list_page(section.get("contents") or [], extract_client_version(html))


def parse_playlist_continuation(payload: dict[str, Any], continuation: Continuation) -> VideoPage:
    """The next page of the list of a playlist, from the response of the ``browse`` endpoint."""
    return _list_page(find_key("continuationItems", payload, list) or [], continuation.client_version)
