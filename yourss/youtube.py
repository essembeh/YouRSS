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


def yt_parse_channel_id(channel_url: str) -> str | None:
    parsed_url = urlparse(channel_url)
    assert parsed_url.hostname in YT_HOSTS, f"Invalid host: {parsed_url.hostname}"
    last_segment = parsed_url.path.split("/")[-1]
    if re.fullmatch(CHANNEL_PATTERN, last_segment):
        return last_segment


def yt_rss_url(channel_id: str | None = None, user: str | None = None) -> str:
    if channel_id is not None:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    if user is not None:
        return f"https://www.youtube.com/feeds/videos.xml?user={user}"
    raise ValueError()


def yt_home_url(
    slug: str | None = None,
    channel_id: str | None = None,
    user: str | None = None,
    magic: str | None = None,
) -> str:
    if magic is not None:
        if magic.startswith("@"):
            return yt_home_url(slug=magic)
        elif re.fullmatch(CHANNEL_PATTERN, magic):
            return yt_home_url(channel_id=magic)
        else:
            return yt_home_url(user=magic)
    if slug is not None:
        assert slug.startswith("@")
        return f"https://www.youtube.com/{slug}"
    if channel_id is not None:
        assert re.fullmatch(CHANNEL_PATTERN, channel_id)
        return f"https://www.youtube.com/channel/{channel_id}"
    if user is not None:
        return f"https://www.youtube.com/user/{user}"
    raise ValueError()


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


def youtube_fetch_rss_feed(name: str) -> requests.Response:
    feed_url = None
    if name.startswith("@"):
        # parse homepage metadata
        metadata = YoutubeScrapper.fromresponse(yt_html_get(yt_home_url(slug=name)))
        # find channelid
        channel_id = metadata.find_channel_id()
        # fetch rss feed
        feed_url = yt_rss_url(channel_id=channel_id)
    elif re.fullmatch(CHANNEL_PATTERN, name):
        # fetch rss feed
        feed_url = yt_rss_url(channel_id=name)
    else:
        # fetch rss feed
        feed_url = yt_rss_url(user=name)

    resp = yt_request(feed_url)
    resp.raise_for_status()
    return resp
