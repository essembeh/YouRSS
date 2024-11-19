from asyncio import sleep
from dataclasses import dataclass
from typing import Annotated, Any, AsyncIterator, Dict, List, Literal

from pydantic import TypeAdapter
from rapid_api_client import Path, Query
from rapid_api_client.annotations import JsonBody
from rapid_api_client.async_ import AsyncRapidApi, get, post

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


@dataclass
class YoutubeApi(AsyncRapidApi):
    def __post_init__(self):
        self.client.base_url = BASE_URL
        self.client.follow_redirects = True
        self.client.headers["user-agent"] = MOZILLA_USER_AGENT
        self.client.headers["accept-language"] = "en"
        self.client.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")

    @get("/feeds/videos.xml?channel_id={channel_id}", response_class=Feed)
    async def get_channel_rss(self, channel_id: Annotated[str, Path()]): ...

    @get("/feeds/videos.xml?playlist_id={playlist_id}", response_class=Feed)
    async def get_playlist_rss(self, playlist_id: Annotated[str, Path()]): ...

    @get("{path}")
    async def get_html(
        self, path: Annotated[str, Path()], ucbcb: Annotated[int, Query(default=1)]
    ): ...

    @post("/youtubei/v1/browse", response_class=TypeAdapter(Dict[str, Any]))
    async def api_browse(self, data: Annotated[dict, JsonBody()]): ...

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
