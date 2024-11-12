from dataclasses import dataclass
from typing import Annotated, Any, Dict

from httpx import Response
from pydantic import TypeAdapter
from rapid_api_client import FormBody, Path, Query
from rapid_api_client.annotations import JsonBody
from rapid_api_client.async_ import AsyncRapidApi, get, post

from .schema import Feed
from .utils import (
    MOZILLA_USER_AGENT,
    is_channel_id,
    is_user,
)

BASE_URL = "https://www.youtube.com"
CHANNEL_RSS_URL = "/feeds/videos.xml?channel_id={channel_id}"
PLAYLIST_RSS_URL = "/feeds/videos.xml?playlist_id={playlist_id}"


@dataclass
class YoutubeWebApi(AsyncRapidApi):
    def __post_init__(self):
        self.client.base_url = BASE_URL
        self.client.follow_redirects = True
        self.client.headers["user-agent"] = MOZILLA_USER_AGENT
        self.client.headers["accept-language"] = "en"
        self.client.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")

    @get("{path}")
    async def get_html(
        self, path: Annotated[str, Path()], ucbcb: Annotated[int, Query(default=1)]
    ): ...

    @post("{path}")
    async def post_html(
        self, path: Annotated[str, Path()], form: Annotated[Dict, FormBody()]
    ): ...

    @post("/youtubei/v1/browse", response_class=TypeAdapter(Dict[str, Any]))
    async def api_browse(self, data: Annotated[dict, JsonBody()]): ...

    async def get_homepage(self, name: str) -> Response:
        if is_channel_id(name):
            return await self.get_html(f"/channel/{name}")
        if is_user(name):
            return await self.get_html(f"/{name}")
        raise ValueError(f"Cannot find homepage for: {name}")


@dataclass
class YoutubeRssApi(AsyncRapidApi):
    def __post_init__(self):
        self.client.base_url = BASE_URL

    @get(CHANNEL_RSS_URL, response_class=Feed)
    async def get_channel_rss(self, channel_id: Annotated[str, Path()]): ...

    @get(PLAYLIST_RSS_URL, response_class=Feed)
    async def get_playlist_rss(self, playlist_id: Annotated[str, Path()]): ...
