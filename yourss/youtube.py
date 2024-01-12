from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from httpx import AsyncClient, Response
from loguru import logger

from .model import RssFeed

YT_HOSTS = ["consent.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"]

OG_URL = "og:url"
OG_IMAGE = "og:image"
OG_TITLE = "og:title"
OG_TYPE = "og:type"

MOZILLA_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
)

CHANNEL_PATTERN = r"[a-zA-Z0-9_-]{24}"


def create_client(
    timeout: int = 10,
    user_agent: str = MOZILLA_USER_AGENT,
    follow_redirects: bool = True,
) -> AsyncClient:
    return AsyncClient(
        headers={"user-agent": user_agent},
        timeout=timeout,
        follow_redirects=follow_redirects,
    )


@dataclass
class YoutubeScrapper:
    soup: BeautifulSoup

    @classmethod
    def fromresponse(cls, resp: Response) -> YoutubeScrapper:
        resp.raise_for_status()
        assert resp.headers.get("content-type", "").startswith("text/html")
        return cls(BeautifulSoup(resp.text, features="html.parser"))

    @cached_property
    def metadata(self) -> dict[str, str]:
        return {
            m["property"]: m.get("content")
            for m in self.soup.find_all("meta")
            if "property" in m.attrs
        }

    @property
    def title(self) -> str | None:
        return self.metadata.get(OG_TITLE)

    @property
    def avatar_url(self) -> str | None:
        return self.metadata.get(OG_IMAGE)

    @property
    def homepage_url(self) -> str | None:
        return self.metadata.get(OG_URL)

    def find_channel_id(self) -> str | None:
        if (url := self.homepage_url) is not None:
            parsed_url = urlparse(url)
            assert (
                parsed_url.hostname in YT_HOSTS
            ), f"Invalid host: {parsed_url.hostname}"
            last_segment = parsed_url.path.split("/")[-1]
            if re.fullmatch(CHANNEL_PATTERN, last_segment):
                return last_segment
        # results = re.findall(r'@id":\s"(\S+)"', str(self.soup.select("script")))
        # if len(results) > 0:
        #     return yt_magic_find_channel_id(results[0].replace("\\", ""))


class YoutubeUrl:
    @staticmethod
    def thumbnail(video_id: str, instance: int = 1) -> str:
        return f"https://i{instance}.ytimg.com/vi/{video_id}/hqdefault.jpg"

    @staticmethod
    def channel_rss(channel_id: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    @staticmethod
    def user_rss(user: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?user={user}"

    @staticmethod
    def playlist_rss(playlist: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist}"

    @classmethod
    def slug_home(cls, slug: str) -> str:
        assert slug.startswith("@")
        return f"https://www.youtube.com/{slug}"

    @classmethod
    def channel_home(cls, channel_id: str) -> str:
        assert re.fullmatch(CHANNEL_PATTERN, channel_id)
        return f"https://www.youtube.com/channel/{channel_id}"

    @classmethod
    def user_home(cls, user: str) -> str:
        return f"https://www.youtube.com/user/{user}"

    @classmethod
    def home(cls, anything: str) -> str:
        if anything.startswith("@"):
            logger.debug("Guess {} looks like a slug", anything)
            return cls.slug_home(anything)
        elif re.fullmatch(CHANNEL_PATTERN, anything):
            logger.debug("Guess {} looks like a channel", anything)
            return cls.channel_home(anything)
        else:
            logger.debug("Guess {} looks like a user", anything)
            return cls.user_home(anything)


@dataclass
class YoutubeWebClient:
    client: AsyncClient = field(default_factory=create_client)

    async def _request(
        self,
        youtube_url: str,
        method: str = "get",
        **kwargs,
    ) -> Response:
        parsed_url = urlparse(youtube_url)
        assert parsed_url.hostname in YT_HOSTS, f"Invalid host: {parsed_url.hostname}"

        response = await self.client.request(
            method,
            youtube_url,
            follow_redirects=True,
            **kwargs,
        )
        logger.debug("Youtube {} {}: {}", method, youtube_url, response.status_code)
        return response

    async def get_html(self, youtube_url: str) -> Response:
        """
        get a youtube page content with cookie accept if needed
        """
        response = await self._request(youtube_url)
        response.raise_for_status()
        # check response is an html page
        if response.headers.get("content-type", "").startswith("text/html"):
            # check for the cookie accep form
            soup = BeautifulSoup(response.text, features="html.parser")
            forms = soup.find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
            logger.debug("Found {} forms in html page", len(forms))
            if len(forms) > 0:
                form = forms[0]
                logger.debug("Auto accept youtube consent {}", form.attrs)
                response = await self._request(
                    (form.attrs["action"]),
                    method="post",
                    data={
                        element.attrs["name"]: element.attrs["value"]
                        for element in form.find_all("input")
                        if "name" in element.attrs and "value" in element.attrs
                    },
                )
                response.raise_for_status()

        return response

    async def get_metadata(self, name: str) -> YoutubeScrapper:
        return YoutubeScrapper.fromresponse(await self.get_html(YoutubeUrl.home(name)))

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
        resp = await self._request(feed_url)
        resp.raise_for_status()
        return resp.text

    async def get_rss_feed(self, name: str) -> RssFeed:
        return RssFeed.fromstring(await self.get_rss_xml(name))

    async def get_avatar_url(self, name: str) -> str | None:
        meta = await self.get_metadata(name)
        return meta.avatar_url
