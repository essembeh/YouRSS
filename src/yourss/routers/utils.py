from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from ..youtube import ChannelDescription, Continuation, Feed, VideoDescription, is_user
from ..youtube.cache import channel_cache

# Sort key of a video without a date (never the case for an RSS entry)
_OLDEST = datetime.min.replace(tzinfo=UTC)


def split_subscriptions(text: str, delimiter: str = ",") -> list[str]:
    """Names of an address, in their order, without duplicates."""
    return list(dict.fromkeys(name for name in map(str.strip, text.split(delimiter)) if name))


def page_entries(
    names: list[str], channels: dict[str, ChannelDescription], feeds: list[Feed]
) -> tuple[list[ChannelDescription], list[Feed]]:
    """What the sidebar lists: the channels and the playlists named by the page, sorted by name."""
    listed = [channel for channel in channels.values() if channel.channel_id in names]
    playlists = [feed for feed in feeds if feed.playlist_id is not None and feed.playlist_id in names]
    return sorted(listed, key=lambda c: c.name.lower()), sorted(playlists, key=lambda f: f.title.lower())


def canonical_names(names: list[str]) -> list[str]:
    """Subscriptions of a user page for the address of its copy: the id of each handle the cache knows."""
    out = []
    for name in names:
        cached = channel_cache.get(name) if is_user(name) else None
        out.append(cached.channel_id if cached is not None else name)
    return list(dict.fromkeys(out))


def build_url(base_url: str, params: dict[str, Any]) -> str:
    return base_url + "?" + urlencode(params)


def next_page_url(continuation: Continuation | None, *, shorts: bool) -> str | None:
    """URL of the htmx request which appends the next page of a channel tab."""
    if continuation is None:
        return None
    return build_url(
        "/htmx/next",
        {
            "token": continuation.token,
            "version": continuation.client_version,
            "shorts": shorts,
        },
    )


def get_videos_from_feeds(feeds: list[Feed], channels: dict[str, ChannelDescription]) -> list[VideoDescription]:
    """Every video of the feeds, newest first, each one attached to its channel."""
    out = []
    for feed in feeds:
        for entry in feed.entries:
            channel = channels.get(entry.channel_id) or ChannelDescription(
                channel_id=entry.channel_id,
                name=entry.author.name,
                home=str(entry.author.uri),
            )
            out.append(entry.to_video(channel))
    out.sort(key=lambda v: v.published_at or _OLDEST, reverse=True)
    # A video present in two feeds (a channel and one of its playlists) is listed once
    return list({video.video_id: video for video in reversed(out)}.values())[::-1]
