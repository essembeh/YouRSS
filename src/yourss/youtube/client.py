from asyncio import sleep
from typing import (
    Annotated,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
)

from httpx import Cookies, HTTPStatusError, Response
from loguru import logger
from rapid_api_client import JsonBody, Path, Query, RapidApi, get, post, rapid
from starlette.status import HTTP_404_NOT_FOUND

from ..settings import current_config
from .cache import read_stale_feed, write_cached_feed
from .model import BrowseData, VideoDescription
from .schema import Feed
from .scrapper import PageScrapper
from .utils import (
    is_channel_id,
    is_user,
)

BASE_URL = "https://www.youtube.com"
MOZILLA_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
)


def _youtube_cookies() -> Cookies:
    out = Cookies()
    out.set("CONSENT", "YES+cb", domain=".youtube.com")
    return out


@rapid(
    base_url=BASE_URL,
    headers={"user-agent": MOZILLA_USER_AGENT, "accept-language": "en"},
    follow_redirects=True,
    cookies=_youtube_cookies(),
)
class YoutubeApi(RapidApi):
    @get("/feeds/videos.xml")
    async def _get_channel_rss_raw(
        self, channel_id: Annotated[str, Query()]
    ) -> Feed: ...

    @get("/feeds/videos.xml")
    async def _get_playlist_rss_raw(
        self, playlist_id: Annotated[str, Query()]
    ) -> Feed: ...

    async def _fetch_rss(
        self, key: str, fetch: Callable[[str], Awaitable[Feed]]
    ) -> Feed:
        """Always fetch the feed live. The on-disk copy is only a fallback used
        when Youtube returns a transient 404 (it does so daily on all feeds)."""
        folder = current_config.cache_folder
        if folder is None:
            return await fetch(key)
        try:
            feed = await fetch(key)
        except HTTPStatusError as error:
            if error.response.status_code != HTTP_404_NOT_FOUND:
                raise
            logger.warning("Youtube returned 404 for RSS {}", key)
            stale = read_stale_feed(folder, key, current_config.cache_max_age)
            if stale is not None:
                return stale
            raise
        write_cached_feed(folder, key, feed._response.content)
        return feed

    async def get_channel_rss(self, channel_id: str) -> Feed:
        return await self._fetch_rss(channel_id, self._get_channel_rss_raw)

    async def get_playlist_rss(self, playlist_id: str) -> Feed:
        return await self._fetch_rss(playlist_id, self._get_playlist_rss_raw)

    @get("{path}")
    async def get_html(
        self, path: Annotated[str, Path()], ucbcb: Annotated[int, Query()] = 1
    ) -> Response: ...

    @post("/youtubei/v1/browse")
    async def api_browse(self, data: Annotated[dict, JsonBody()]) -> Dict[str, Any]: ...

    async def get_homepage(
        self, name: str, suffix: Literal["/videos", "/shorts", "/streams"] | None = None
    ) -> PageScrapper:
        if is_channel_id(name):
            resp = await self.get_html(f"/channel/{name}{suffix or ''}")
        elif is_user(name):
            resp = await self.get_html(f"/{name}{suffix or ''}")
        else:
            raise ValueError(f"Cannot find homepage for: {name}")
        return PageScrapper.from_response(resp)

    async def iter_videos(
        self, channel: str, *, delay: float = 0
    ) -> AsyncIterator[List[VideoDescription]]:
        homepage = await self.get_homepage(channel, suffix="/videos")
        assert (client_data := homepage.find_client_data()) is not None
        assert (browse_data := homepage.find_browse_data()) is not None
        while True:
            videos = list(browse_data.iter_videos())
            if len(videos) > 0:
                # yield all videos from the page
                yield videos
            else:
                # could not find any video
                break
            if browse_data.continuation_token is None:
                # no continuation token, stop
                break
            # get next page using json api
            if delay > 0:
                await sleep(delay)
            browse_data = await self.get_next_page(
                client_data,
                browse_data.click_tracking_params,
                browse_data.continuation_token,
            )

    async def get_next_page(
        self,
        client_data: Dict[str, Any],
        click_tracking_params: str,
        continuation_token: str,
    ) -> BrowseData:
        resp = await self.api_browse(
            {
                "context": {
                    "clickTracking": {"clickTrackingParams": click_tracking_params},
                    "client": client_data,
                },
                "continuation": continuation_token,
            }
        )
        return BrowseData(resp)
