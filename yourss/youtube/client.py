from dataclasses import dataclass
from typing import Annotated, Any, Dict, Literal

from httpx import Response
from pydantic import TypeAdapter
from rapid_api_client import Path, Query
from rapid_api_client.annotations import JsonBody
from rapid_api_client.async_ import AsyncRapidApi, get, post

from .schema import Feed
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
        self, name: str, suffix: Literal["/videos"] | None = None
    ) -> Response:
        if is_channel_id(name):
            return await self.get_html(f"/channel/{name}{suffix or ''}")
        if is_user(name):
            return await self.get_html(f"/{name}{suffix or ''}")
        raise ValueError(f"Cannot find homepage for: {name}")
