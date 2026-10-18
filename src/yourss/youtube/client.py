from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated, Any

from httpx import Cookies, Response
from loguru import logger
from rapid_api_client import JsonBody, Path, Query, RapidApi, get, post, rapid_default

from ..settings import current_config
from .cache import (
    cache_folder,
    drop_cached_feed,
    read_cached_channel,
    read_cached_feed,
    write_cached_channel,
    write_cached_feed,
)
from .model import ChannelDescription, VideoDescription
from .schema import Feed
from .scraping import (
    ChannelPage,
    ChannelTab,
    Continuation,
    ScrapingError,
    VideoPage,
    parse_channel_page,
    parse_continuation,
)
from .utils import is_channel_id, is_user, parse_channel_reference

BASE_URL = "https://www.youtube.com"
MOZILLA_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"


def _youtube_cookies() -> Cookies:
    out = Cookies()
    out.set("CONSENT", "YES+cb", domain=".youtube.com")
    return out


@rapid_default(
    base_url=BASE_URL,
    headers={"user-agent": MOZILLA_USER_AGENT, "accept-language": "en"},
    follow_redirects=True,
    cookies=_youtube_cookies(),
)
class YoutubeApi(RapidApi):
    """
    Transport only: what is asked to Youtube and how. Reading the answers is the
    job of the ``schema`` module (RSS) and of the ``scraping`` package (pages).
    """

    # Endpoints declared with `...`: rapid-api-client implements them, hence the empty-body ignores

    # --- RSS feeds

    @get("/feeds/videos.xml")
    async def _get_channel_rss_raw(self, channel_id: Annotated[str, Query()]) -> Feed: ...  # type: ignore[empty-body]

    @get("/feeds/videos.xml")
    async def _get_playlist_rss_raw(self, playlist_id: Annotated[str, Query()]) -> Feed: ...  # type: ignore[empty-body]

    async def _fetch_rss(self, key: str, fetch: Callable[[str], Awaitable[Feed]], *, refresh: bool) -> Feed:
        """Fetch a feed through the optional disk cache (docs/specs/disk-cache.md); `refresh` ignores a fresh copy."""
        folder = cache_folder()
        if folder is None:
            return await fetch(key)
        cached = None if refresh else read_cached_feed(folder, key, current_config.cache_rss_ttl)
        if cached is not None:
            return cached
        try:
            feed = await fetch(key)
        except Exception as error:
            # Any failure (Youtube's daily transient 404, 5xx, network) falls back on the cache
            stale = read_cached_feed(folder, key, current_config.cache_rss_fallback_ttl)
            if stale is None:
                drop_cached_feed(folder, key)
                raise
            logger.warning("Serving the cached RSS of {} after a fetch error: {}", key, error)
            return stale
        write_cached_feed(folder, key, feed._response.content)
        return feed

    async def get_channel_rss(self, channel_id: str, *, refresh: bool = False) -> Feed:
        return await self._fetch_rss(channel_id, self._get_channel_rss_raw, refresh=refresh)

    async def get_playlist_rss(self, playlist_id: str, *, refresh: bool = False) -> Feed:
        return await self._fetch_rss(playlist_id, self._get_playlist_rss_raw, refresh=refresh)

    # --- oEmbed, the public endpoint which names the channel of a video

    @get("/oembed")
    async def _get_oembed(self, url: Annotated[str, Query()]) -> dict[str, Any]: ...  # type: ignore[empty-body]

    async def get_video_channel(self, video_id: str) -> str:
        """Handle or id of the channel which published a video."""
        embed = await self._get_oembed(f"{BASE_URL}/watch?v={video_id}")
        out = parse_channel_reference(str(embed.get("author_url", "")))
        if out is None:
            raise ScrapingError(f"No channel in the oEmbed answer for video {video_id}: {embed!r}")
        return out

    # --- pages and internal API, read by the scraping package

    @get("{path}")
    async def get_html(self, path: Annotated[str, Path()], ucbcb: Annotated[int, Query()] = 1) -> Response: ...  # type: ignore[empty-body]

    @post("/youtubei/v1/browse")
    async def api_browse(self, data: Annotated[dict[str, Any], JsonBody()]) -> dict[str, Any]: ...  # type: ignore[empty-body]

    async def get_channel_page(self, name: str, tab: ChannelTab | None = None) -> ChannelPage:
        """Page of a channel (``UC…`` id or ``@handle``): its home, or one of its tabs."""
        if is_channel_id(name):
            path = f"/channel/{name}"
        elif is_user(name):
            path = f"/{name}"
        else:
            raise ValueError(f"Cannot find homepage for: {name}")
        url = f"{path}/{tab}" if tab else path
        try:
            out = parse_channel_page(await self._get_page(url))
        except ScrapingError as error:
            # Youtube sometimes serves a page in another layout: a second request usually gets the usual one
            logger.warning("Retrying {}: {}", url, error)
            out = parse_channel_page(await self._get_page(url))
        if (folder := cache_folder()) is not None:
            write_cached_channel(folder, name, out.channel)
        return out

    async def _get_page(self, url: str) -> str:
        resp = await self.get_html(url)
        resp.raise_for_status()
        return resp.text

    async def get_channel(self, name: str) -> ChannelDescription:
        """Name, id, avatar and home of a channel, through the optional disk cache (docs/specs/disk-cache.md)."""
        folder = cache_folder()
        if folder is None:
            return (await self.get_channel_page(name)).channel
        cached = read_cached_channel(folder, name, current_config.cache_metadata_ttl)
        if cached is not None:
            return cached
        try:
            return (await self.get_channel_page(name)).channel
        except Exception as error:
            # A stale name or avatar is harmless: the cached description is served whatever its age
            stale = read_cached_channel(folder, name, None)
            if stale is None:
                raise
            logger.warning("Serving the cached description of {} after a fetch error: {}", name, error)
            return stale

    async def get_more_videos(self, continuation: Continuation, *, shorts: bool = False) -> VideoPage:
        """Next page of a channel tab."""
        payload = await self.api_browse(
            {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": continuation.client_version,
                        "hl": "en",
                    }
                },
                "continuation": continuation.token,
            }
        )
        return parse_continuation(payload, continuation, shorts=shorts)

    async def iter_videos(self, channel: str) -> AsyncIterator[list[VideoDescription]]:
        """Every video of a channel, one page at a time."""
        page = (await self.get_channel_page(channel, "videos")).videos()
        while page.videos:
            yield page.videos
            if page.continuation is None:
                break
            page = await self.get_more_videos(page.continuation)
