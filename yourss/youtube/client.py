from dataclasses import dataclass
from typing import Annotated, Dict
from urllib.parse import urlparse

from httpx import Response
from loguru import logger
from rapid_api_client import FormBody, Path
from rapid_api_client.async_ import AsyncRapidApi, get, post

from .schema import Feed
from .utils import (
    ALLOWED_HOSTS,
    MOZILLA_USER_AGENT,
    html_get_rgpd_forms,
    is_channel_id,
    is_user,
)

BASE_URL = "https://www.youtube.com"
CHANNEL_RSS_URL = "/feeds/videos.xml?channel_id={channel_id}"
PLAYLIST_RSS_URL = "/feeds/videos.xml?playlist_id={playlist_id}"


@dataclass
class YoutubeWebApi(AsyncRapidApi):
    def __post_init__(self):
        self.client.follow_redirects = True
        self.client.headers.setdefault("user-agent", MOZILLA_USER_AGENT)

    @get("{url}")
    async def get_html(self, url: Annotated[str, Path()]): ...

    @post("{url}")
    async def post_html(
        self, url: Annotated[str, Path()], form: Annotated[Dict, FormBody()]
    ): ...

    async def get_rgpd_html(self, url: str) -> Response:
        logger.debug("Get youtube page: {}", url)
        parsed_url = urlparse(url)
        assert (
            parsed_url.hostname in ALLOWED_HOSTS
        ), f"Invalid host: {parsed_url.hostname}"
        response = await self.get_html(url)
        response.raise_for_status()
        if len(forms := html_get_rgpd_forms(response.text)) > 0:
            logger.debug("Page {} has RGPD forms", url)
            response = await self.post_html(
                (forms[0].attrs["action"]),
                form={
                    element.attrs["name"]: element.attrs["value"]
                    for element in forms[0].find_all("input")
                    if "name" in element.attrs and "value" in element.attrs
                },
            )
            response.raise_for_status()
        return response

    async def get_homepage(self, name: str) -> Response:
        if is_channel_id(name):
            return await self.get_rgpd_html(f"https://www.youtube.com/channel/{name}")
        if is_user(name):
            return await self.get_rgpd_html(f"https://www.youtube.com/{name}")
        raise ValueError(f"Cannot find homepage for: {name}")


@dataclass
class YoutubeRssApi(AsyncRapidApi):
    def __post_init__(self):
        self.client.base_url = BASE_URL

    @get(CHANNEL_RSS_URL, response_class=Feed)
    async def get_channel_rss(self, channel_id: Annotated[str, Path()]): ...

    @get(PLAYLIST_RSS_URL, response_class=Feed)
    async def get_playlist_rss(self, playlist_id: Annotated[str, Path()]): ...
