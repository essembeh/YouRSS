"""Read a Youtube channel page (home or one of its tabs) and a continuation response."""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from glom import Coalesce, glom  # type: ignore[import-untyped]  # glom has no type hints
from pydantic import BaseModel

from ..model import ChannelDescription, PlaylistDescription, VideoDescription
from ..utils import parse_channel_reference
from .errors import ScrapingError
from .extract import extract_client_version, extract_initial_data
from .items import parse_playlist_cards, parse_videos
from .walk import find_key, iter_key

# Tabs of a channel, named after the last segment of their Youtube URL
ChannelTab = Literal["videos", "shorts", "streams", "playlists"]
CHANNEL_TABS: tuple[str, ...] = get_args(ChannelTab)
# The tabs listing playlists rather than videos
PLAYLIST_TABS: tuple[str, ...] = ("playlists",)

# Where things live in ytInitialData: the only place to touch when Youtube moves them
_CHANNEL = Coalesce("metadata.channelMetadataRenderer", default=None)
_CHANNEL_AVATAR = Coalesce("avatar.thumbnails.0.url", default=None)
_TAB_URL = Coalesce("endpoint.commandMetadata.webCommandMetadata.url", default="")
_AVATAR_SIZE = re.compile(r"=s\d+(?=-|$)")
AVATAR_SIZE = 176


class Continuation(BaseModel, frozen=True):
    """What is needed to ask Youtube for the next page of a tab."""

    token: str
    client_version: str


class VideoPage(BaseModel):
    videos: list[VideoDescription]
    continuation: Continuation | None = None


def _video_page(payload: dict[str, Any], client_version: str | None, shorts: bool) -> VideoPage:
    command = find_key("continuationCommand", payload, dict)
    token = command.get("token") if command else None
    return VideoPage(
        videos=parse_videos(payload, shorts=shorts),
        continuation=Continuation(token=token, client_version=client_version) if token and client_version else None,
    )


class PlaylistCardPage(BaseModel):
    playlists: list[PlaylistDescription]
    continuation: Continuation | None = None


# The last item of a list loads its next page; a continuation elsewhere (a side panel, suggestions) loads something else
_CONTINUATION_ITEMS = ("continuationItemViewModel", "continuationItemRenderer")


def list_continuation_token(items: list[Any]) -> str | None:
    """The token of the next page of a list, held by its last item when there is one."""
    last = items[-1] if items else None
    if not isinstance(last, dict) or not any(key in last for key in _CONTINUATION_ITEMS):
        return None
    # A continuation item nests a tokenless command around the one holding the token
    return next(
        (command["token"] for command in iter_key("continuationCommand", last, dict) if command.get("token")), None
    )


def _card_items(payload: dict[str, Any]) -> list[Any]:
    # Playlists sit in a grid, a next page in the items of a continuation
    if (grid := find_key("gridRenderer", payload, dict)) is not None:
        return list(grid.get("items") or [])
    return list(find_key("continuationItems", payload, list) or [])


def _playlist_card_page(payload: dict[str, Any], client_version: str | None) -> PlaylistCardPage:
    items = _card_items(payload)
    token = list_continuation_token(items)
    return PlaylistCardPage(
        playlists=parse_playlist_cards({"items": items}),
        continuation=Continuation(token=token, client_version=client_version) if token and client_version else None,
    )


@dataclass(frozen=True)
class ChannelPage:
    channel: ChannelDescription
    # Tabs the channel really has, and the one this page displays (None on the channel home)
    tabs: list[str]
    selected_tab: str | None
    client_version: str | None = field(repr=False)
    data: dict[str, Any] = field(repr=False)

    def videos(self, *, shorts: bool = False) -> VideoPage:
        """First page of videos (or shorts) displayed by this page."""
        return _video_page(self.data, self.client_version, shorts)

    def playlists(self) -> PlaylistCardPage:
        """First page of playlists displayed by this page (the Playlists tab)."""
        return _playlist_card_page(self.data, self.client_version)


def _parse_channel(data: dict[str, Any]) -> ChannelDescription:
    meta = glom(data, _CHANNEL)
    if not isinstance(meta, dict) or not meta.get("externalId") or not meta.get("title"):
        raise ScrapingError("Cannot find the channel metadata in the Youtube page")
    avatar = glom(meta, _CHANNEL_AVATAR)
    # The vanity address is youtube.com/@name, or the /channel/ one for a channel without a handle
    handle = parse_channel_reference(str(meta.get("vanityChannelUrl") or "")) or ""
    return ChannelDescription(
        channel_id=meta["externalId"],
        name=meta["title"],
        # The page advertises a 900 px avatar, far more than what the UI displays
        avatar=_AVATAR_SIZE.sub(f"=s{AVATAR_SIZE}", avatar) if avatar else "",
        home=meta.get("channelUrl") or f"https://www.youtube.com/channel/{meta['externalId']}",
        handle=handle if handle.startswith("@") else "",
    )


def _iter_tabs(data: dict[str, Any]) -> Iterator[tuple[str, bool]]:
    for tab in iter_key("tabRenderer", data, dict):
        yield glom(tab, _TAB_URL).rsplit("/", 1)[-1], bool(tab.get("selected"))


def parse_channel_page(html: str) -> ChannelPage:
    """Everything the application needs from the HTML of a channel page."""
    data = extract_initial_data(html)
    tabs = list(_iter_tabs(data))
    names = {name for name, _ in tabs}
    # Youtube serves the channel home ("featured") when the requested tab does not exist
    selected = next((name for name, selected in tabs if selected), None)
    return ChannelPage(
        channel=_parse_channel(data),
        tabs=[tab for tab in CHANNEL_TABS if tab in names],
        selected_tab=selected if selected in CHANNEL_TABS else None,
        client_version=extract_client_version(html),
        data=data,
    )


def parse_continuation(payload: dict[str, Any], continuation: Continuation, *, shorts: bool = False) -> VideoPage:
    """Next page of a tab, from the response of the ``browse`` endpoint."""
    return _video_page(payload, continuation.client_version, shorts)


def parse_playlists_continuation(payload: dict[str, Any], continuation: Continuation) -> PlaylistCardPage:
    """Next page of a Playlists tab, from the response of the ``browse`` endpoint."""
    return _playlist_card_page(payload, continuation.client_version)
