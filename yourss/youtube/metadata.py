import re
from dataclasses import dataclass
from functools import cached_property
from typing import Self
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from httpx import Response

YT_HOSTS = ["consent.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"]

OG_URL = "og:url"
OG_IMAGE = "og:image"
OG_TITLE = "og:title"
OG_TYPE = "og:type"


CHANNEL_PATTERN = r"UC[a-zA-Z0-9_-]{22}"


@dataclass
class YoutubeMetadata:
    soup: BeautifulSoup

    @classmethod
    def fromresponse(cls, resp: Response) -> Self:
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
