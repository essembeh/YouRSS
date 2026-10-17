from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict
from urllib.parse import quote, urlencode

from pydantic import BaseModel

from ..async_utils import Kind, SubscriptionStatus
from ..youtube import ChannelDescription, Continuation, Feed, VideoDescription
from ..youtube.cache import known_channel

# Sort key of a video without a date (never the case for an RSS entry)
_OLDEST = datetime.min.replace(tzinfo=UTC)


def split_subscriptions(text: str, delimiter: str = ",") -> list[str]:
    """Names of an address, in their order, without duplicates."""
    return list(dict.fromkeys(name for name in map(str.strip, text.split(delimiter)) if name))


def page_entries(statuses: list[SubscriptionStatus]) -> list[SubscriptionStatus]:
    """What the sidebar lists, every subscription whatever its state (docs/specs/fetch-errors.md §3).

    Channels with a name by name, then playlists with a title by title, then what has no name by raw id.
    """
    channels = [s for s in statuses if s.kind is Kind.CHANNEL and s.label is not None]
    playlists = [s for s in statuses if s.kind is Kind.PLAYLIST and s.label is not None]
    unnamed = [s for s in statuses if s.label is None]
    return (
        sorted(channels, key=lambda s: (s.label or "").lower())
        + sorted(playlists, key=lambda s: (s.label or "").lower())
        + sorted(unnamed, key=lambda s: s.name)
    )


def canonical_names(statuses: list[SubscriptionStatus]) -> list[str]:
    """Subscriptions of a user page for the address of its copy: the id of each handle that was resolved."""
    return list(dict.fromkeys(status.id for status in statuses))


def age_text(age: timedelta) -> str:
    """A rounded age for the visitor: "3 hours", "2 days", "less than a minute"."""
    seconds = age.total_seconds()
    if seconds >= 2 * 86400:
        return f"{int(seconds // 86400)} days"
    if seconds >= 3600:
        hours = int(seconds // 3600)
        return "1 hour" if hours == 1 else f"{hours} hours"
    if seconds >= 60:
        minutes = int(seconds // 60)
        return "1 minute" if minutes == 1 else f"{minutes} minutes"
    return "less than a minute"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


class FetchSummary(BaseModel, frozen=True):
    """The one line notice of a page, and the subscriptions it details (docs/specs/fetch-errors.md §4)."""

    line: str
    # One (name, explanation) per detailed subscription, empty when the sidebar markers are enough
    details: list[tuple[str, str]] = []


def fetch_summary(statuses: list[SubscriptionStatus]) -> FetchSummary | None:
    failed = [s for s in statuses if s.failed]
    stale = [s for s in statuses if s.stale]
    if not failed and not stale:
        return None
    if not failed:
        oldest = max(s.age or timedelta(0) for s in stale)
        verb = "shows" if len(stale) == 1 else "show"
        prefix = "" if len(stale) == 1 else "up to "
        return FetchSummary(
            line=f"{_plural(len(stale), 'subscription')} {verb} a cached copy, {prefix}{age_text(oldest)} old.",
            details=[(s.label or s.name, f"cached copy, {age_text(s.age or timedelta(0))} old") for s in stale],
        )
    if len(failed) * 2 >= len(statuses):
        line = "Youtube seems unavailable right now: most subscriptions could not be refreshed"
        details: list[tuple[str, str]] = []
    else:
        line = f"{len(failed)} of {_plural(len(statuses), 'subscription')} could not be refreshed"
        details = [(s.label or s.name, s.reason or "") for s in failed]
    if stale:
        line += f", {_plural(len(stale), 'other')} {'shows' if len(stale) == 1 else 'show'} a cached copy"
    return FetchSummary(line=line + ".", details=details)


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
    """Every video of the feeds, newest first, each one attached to its channel.

    A channel the page does not know is read from the cache, else described from the feed entry.
    """
    channels = dict(channels)
    out = []
    for feed in feeds:
        for entry in feed.entries:
            channel = channels.get(entry.channel_id)
            if channel is None:
                channel = known_channel(entry.channel_id) or ChannelDescription(
                    channel_id=entry.channel_id,
                    name=entry.author.name,
                    home=str(entry.author.uri),
                )
                channels[entry.channel_id] = channel
            out.append(entry.to_video(channel))
    out.sort(key=lambda v: v.published_at or _OLDEST, reverse=True)
    # A video present in two feeds (a channel and one of its playlists) is listed once
    return list({video.video_id: video for video in reversed(out)}.values())[::-1]


class PageContext(TypedDict):
    """What a page or a folder gets from the statuses: sidebar entries, videos, notice."""

    entries: list[SubscriptionStatus]
    videos: list[VideoDescription]
    summary: FetchSummary | None


def page_context(statuses: list[SubscriptionStatus]) -> PageContext:
    feeds = [s.feed for s in statuses if s.feed is not None]
    channels = {s.channel.channel_id: s.channel for s in statuses if s.channel is not None}
    return {
        "entries": page_entries(statuses),
        "videos": get_videos_from_feeds(feeds, channels),
        "summary": fetch_summary(statuses),
    }


def folder_link_prefix(user_name: str, page_name: str) -> str:
    """Start of the links of a folder, `<prefix>c=<id>`: its own address, whatever the page the visitor comes from."""
    return f"/u/{quote(user_name)}/{quote(page_name)}?"
