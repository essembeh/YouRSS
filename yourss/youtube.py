from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

YT_HOSTS = ["consent.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"]

OG_URL = "og:url"
OG_IMAGE = "og:image"
OG_TITLE = "og:title"
OG_TYPE = "og:type"

MOZILLA_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
)

CHANNEL_PATTERN = r"[a-zA-Z0-9_-]{24}"


@dataclass
class YoutubeScrapper:
    soup: BeautifulSoup

    @classmethod
    def fromresponse(cls, resp: requests.Response) -> YoutubeScrapper:
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
            if (channel_id := yt_parse_channel_id(url)) is not None:
                return channel_id
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
            return cls.slug_home(anything)
        elif re.fullmatch(CHANNEL_PATTERN, anything):
            return cls.channel_home(anything)
        else:
            return cls.user_home(anything)


def yt_parse_channel_id(channel_url: str) -> str | None:
    parsed_url = urlparse(channel_url)
    assert parsed_url.hostname in YT_HOSTS, f"Invalid host: {parsed_url.hostname}"
    last_segment = parsed_url.path.split("/")[-1]
    if re.fullmatch(CHANNEL_PATTERN, last_segment):
        return last_segment


def yt_request(
    youtube_url: str,
    method: str = "get",
    check_ok: bool = True,
    timeout: int = 10,
    user_agent: str = MOZILLA_USER_AGENT,
    **kwargs,
) -> requests.Response:
    parsed_url = urlparse(youtube_url)
    assert parsed_url.hostname in YT_HOSTS, f"Invalid host: {parsed_url.hostname}"

    # set default user agent
    headers = kwargs.pop("headers", {})
    headers["user-agent"] = user_agent

    response = requests.request(
        method, youtube_url, headers=headers, timeout=timeout, **kwargs
    )
    logger.debug("Youtube {} {}: {}", method, youtube_url, response.status_code)
    if check_ok:
        response.raise_for_status()
    return response


def yt_html_get(youtube_url: str) -> requests.Response:
    """
    get a youtube page content with cookie accept if needed
    """
    response = yt_request(youtube_url)
    # check response is an html page
    if response.headers.get("content-type", "").startswith("text/html"):
        # check for the cookie accep form
        soup = BeautifulSoup(response.text, features="html.parser")
        forms = soup.find_all(
            "form",
            attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
        )
        if len(forms) > 0:
            response = yt_request(
                (forms[0].attrs["action"]),
                method="post",
                data={
                    element.attrs["name"]: element.attrs["value"]
                    for element in forms[0].find_all("input")
                    if "name" in element.attrs and "value" in element.attrs
                },
            )

    return response


def youtube_get_metadata(name: str) -> YoutubeScrapper:
    return YoutubeScrapper.fromresponse(yt_html_get(YoutubeUrl.home(name)))


def youtube_get_rss_feed(name: str) -> requests.Response:
    feed_url = None
    if name.startswith("@"):
        # parse homepage metadata
        metadata = youtube_get_metadata(name)
        # find channelid
        channel_id = metadata.find_channel_id()
        assert channel_id is not None
        # fetch rss feed
        feed_url = YoutubeUrl.channel_rss(channel_id)
    elif len(name) == 34 and name.startswith("PL"):
        # fetch rss feed
        feed_url = YoutubeUrl.playlist_rss(name)
    elif re.fullmatch(CHANNEL_PATTERN, name):
        # fetch rss feed
        feed_url = YoutubeUrl.channel_rss(name)
    else:
        # fetch rss feed
        feed_url = YoutubeUrl.user_rss(name)

    resp = yt_request(feed_url)
    resp.raise_for_status()
    return resp
