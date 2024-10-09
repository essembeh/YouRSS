from collections import UserDict
from typing import Self
from urllib.parse import ParseResult, urlparse

from httpx import Response

from .utils import ALLOWED_HOSTS, html_get_metadata, is_channel_id


class YoutubeMetadata(UserDict[str, str]):
    @classmethod
    def from_response(cls, resp: Response) -> Self:
        resp.raise_for_status()
        assert resp.headers.get("content-type", "").startswith("text/html")
        return cls(html_get_metadata(resp.text))

    @property
    def title(self) -> str:
        return self["og:title"]

    @property
    def avatar_url(self) -> str | None:
        return self.get("og:image")

    @property
    def url(self) -> ParseResult:
        home_url = self["og:url"]
        out = urlparse(home_url)
        assert out.hostname in ALLOWED_HOSTS, f"Not a valid youtube url: {home_url}"
        return out

    @property
    def channel_id(self) -> str:
        last_segment = self.url.path.split("/")[-1]
        assert is_channel_id(last_segment), f"Invalid channel_id: {last_segment}"
        return last_segment
