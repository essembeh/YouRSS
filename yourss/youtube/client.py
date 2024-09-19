from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from httpx import AsyncClient, Response
from loguru import logger

from ..rss import Feed
from .metadata import CHANNEL_PATTERN, YoutubeMetadata
from .url import YoutubeUrl

ALLOWED_HOSTS = ["consent.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"]

MOZILLA_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
)


class YoutubeClient(AsyncClient):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("follow_redirects", True)
        kwargs.setdefault("headers", {"user-agent": MOZILLA_USER_AGENT})
        super().__init__(*args, **kwargs)

    async def youtube_request(
        self,
        youtube_url: str,
        method: str = "GET",
        **kwargs,
    ) -> Response:
        parsed_url = urlparse(youtube_url)
        assert (
            parsed_url.hostname in ALLOWED_HOSTS
        ), f"Invalid host: {parsed_url.hostname}"

        response = await self.request(method, youtube_url, **kwargs)
        logger.debug(
            "Youtube {} {}: {} in {} sec",
            method,
            youtube_url,
            response.status_code,
            response.elapsed,
        )
        response.raise_for_status()
        return response

    async def get_html(self, youtube_url: str) -> Response:
        """
        get a youtube page content with cookie accept if needed
        """
        response = await self.youtube_request(youtube_url)
        # check response is an html page
        if response.headers.get("content-type", "").startswith("text/html"):
            # check for the cookie accep form
            soup = BeautifulSoup(response.text, features="html.parser")
            forms = soup.find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
            if len(forms) > 0:
                logger.debug("Found {} forms in html page", len(forms))
                form = forms[0]
                logger.debug("Auto accept youtube consent {}", form.attrs)
                response = await self.youtube_request(
                    (form.attrs["action"]),
                    method="post",
                    data={
                        element.attrs["name"]: element.attrs["value"]
                        for element in form.find_all("input")
                        if "name" in element.attrs and "value" in element.attrs
                    },
                )

        return response

    async def get_metadata(self, name: str) -> YoutubeMetadata:
        return YoutubeMetadata.fromresponse(await self.get_html(YoutubeUrl.home(name)))

    async def get_avatar_url(self, name: str) -> str | None:
        meta = await self.get_metadata(name)
        return meta.avatar_url

    async def get_rss_xml(self, name: str) -> str:
        feed_url = None
        if name.startswith("@"):
            logger.debug("Guess {} looks like a slug", name)
            # parse homepage metadata
            metadata = await self.get_metadata(name)
            # find channelid
            channel_id = metadata.find_channel_id()
            assert channel_id is not None
            # fetch rss feed
            feed_url = YoutubeUrl.channel_rss(channel_id)
        elif len(name) == 34 and name.startswith("PL"):
            logger.debug("Guess {} looks like a playlist", name)
            # fetch rss feed
            feed_url = YoutubeUrl.playlist_rss(name)
        elif re.fullmatch(CHANNEL_PATTERN, name):
            logger.debug("Guess {} looks like a channel", name)
            # fetch rss feed
            feed_url = YoutubeUrl.channel_rss(name)
        else:
            logger.debug("Guess {} looks like a user", name)
            # fetch rss feed
            feed_url = YoutubeUrl.user_rss(name)

        logger.debug("Rss feed url for {}: {}", name, feed_url)

        resp = await self.youtube_request(feed_url)
        return resp.text

    async def get_rss_feed(self, name: str) -> Feed:
        return Feed.from_xml(await self.get_rss_xml(name))
