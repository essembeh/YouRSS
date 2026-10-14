import asyncio
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from httpx import HTTPError, HTTPStatusError, TimeoutException
from loguru import logger
from pydantic import BaseModel, ValidationError
from starlette.status import HTTP_404_NOT_FOUND

from .settings import current_config
from .youtube import ChannelDescription, Feed, ScrapingError, YoutubeApi, is_playlist_id, is_user
from .youtube.cache import known_channel


class Kind(StrEnum):
    CHANNEL = "channel"
    PLAYLIST = "playlist"


class State(StrEnum):
    OK = "ok"
    # The feed came from the fallback cache
    STALE = "stale"
    FAILED = "failed"


class SubscriptionStatus(BaseModel, frozen=True):
    """What a page knows about one of its subscriptions after the fetch (docs/specs/fetch-errors.md §2)."""

    # What the page named: UC…, PL… or @handle
    name: str
    kind: Kind
    state: State
    feed: Feed | None = None
    # Resolved from the feed and completed by the cache; None when nothing could be resolved
    channel: ChannelDescription | None = None
    # Age of the cached copy, when stale
    age: timedelta | None = None
    # A short fixed sentence, when failed
    reason: str | None = None

    @property
    def failed(self) -> bool:
        return self.state is State.FAILED

    @property
    def stale(self) -> bool:
        return self.state is State.STALE

    @property
    def id(self) -> str:
        """The channel or playlist id, the raw name when it could not be resolved."""
        if self.kind is Kind.CHANNEL and self.channel is not None:
            return self.channel.channel_id
        return self.name

    @property
    def label(self) -> str | None:
        """The resolved name: the channel name or the playlist title, None when unknown."""
        if self.kind is Kind.PLAYLIST:
            return self.feed.title if self.feed is not None else None
        return self.channel.name if self.channel is not None else None

    @property
    def initial(self) -> str:
        return (self.label or self.name.lstrip("@"))[:1].upper()


def reason_of(error: BaseException) -> str:
    """A fixed sentence for the visitor: the exception itself goes to the logs only."""
    if isinstance(error, HTTPStatusError):
        if error.response.status_code == HTTP_404_NOT_FOUND:
            return "Youtube does not serve this feed right now"
        return "Youtube answered an error"
    if isinstance(error, TimeoutException):
        return "Youtube did not answer in time"
    if isinstance(error, HTTPError):
        return "Youtube could not be reached"
    if isinstance(error, ScrapingError | ValidationError):
        return "Youtube answered something unexpected"
    return "Could not be fetched"


def _failed(name: str, kind: Kind, error: BaseException, channel: ChannelDescription | None) -> SubscriptionStatus:
    logger.warning("Could not fetch {}: {!r}", name, error)
    return SubscriptionStatus(name=name, kind=kind, state=State.FAILED, channel=channel, reason=reason_of(error))


def _fetched(name: str, kind: Kind, feed: Feed, resolved: ChannelDescription | None) -> SubscriptionStatus:
    channel = resolved or known_channel(feed.channel_id)
    if channel is None:
        channel = ChannelDescription(channel_id=feed.channel_id, name=feed.author.name, home=str(feed.author.uri))
    age = datetime.now(UTC) - feed.cached_at if feed.cached_at is not None else None
    if age is not None and age > current_config.cache_rss_ttl:
        return SubscriptionStatus(name=name, kind=kind, state=State.STALE, feed=feed, channel=channel, age=age)
    return SubscriptionStatus(name=name, kind=kind, state=State.OK, feed=feed, channel=channel)


async def async_fetch(names: list[str], api: YoutubeApi) -> list[SubscriptionStatus]:
    """One status per name of the page, in its order: the feeds come first, the metadata is read from the cache."""
    # A handle (user pages only) must be resolved to its id before its feed can be asked
    handles = [name for name in names if is_user(name)]
    resolved = dict(
        zip(handles, await asyncio.gather(*[api.get_channel(h) for h in handles], return_exceptions=True), strict=True)
    )

    targets: dict[str, str] = {}
    for name in names:
        if not is_user(name):
            targets[name] = name
        elif isinstance(channel := resolved[name], ChannelDescription):
            targets[name] = channel.channel_id
    feeds = dict(
        zip(
            targets,
            await asyncio.gather(
                *[api.get_playlist_rss(t) if is_playlist_id(t) else api.get_channel_rss(t) for t in targets.values()],
                return_exceptions=True,
            ),
            strict=True,
        )
    )

    out = []
    for name in names:
        kind = Kind.PLAYLIST if is_playlist_id(name) else Kind.CHANNEL
        if name not in targets:
            error = resolved[name]
            assert isinstance(error, BaseException)  # noqa: S101  # the only reason for a handle to have no target
            out.append(_failed(name, kind, error, known_channel(name)))
            continue
        result = feeds[name]
        if isinstance(result, BaseException):
            out.append(_failed(name, kind, result, known_channel(targets[name]) if kind is Kind.CHANNEL else None))
        else:
            description = resolved.get(name)
            out.append(
                _fetched(name, kind, result, description if isinstance(description, ChannelDescription) else None)
            )
    return out
