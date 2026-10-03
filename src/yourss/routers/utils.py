from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from ..youtube import ChannelDescription, Continuation, Feed, VideoDescription

# Sort key of a video without a date (never the case for an RSS entry)
_OLDEST = datetime.min.replace(tzinfo=UTC)


def force_https(url: str) -> str:
    assert isinstance(url, str)
    if url.startswith("http:"):
        return url.replace("http:", "https:", 1)
    return url


def parse_channel_names(text: str, delimiter: str = ",") -> list[str]:
    return list(set(filter(lambda s: len(s) > 0, map(str.strip, text.split(delimiter)))))


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
    return sorted(out, key=lambda v: v.published_at or _OLDEST, reverse=True)
