import json
import re
from collections import UserDict
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, Iterator, Literal, Self
from urllib.parse import ParseResult, urlparse

from bs4 import BeautifulSoup
from httpx import Response

from yourss.jsonutils import json_first, json_iter

from .utils import ALLOWED_HOSTS, html_get_metadata, is_channel_id

YTCFG_PATTERN = r"ytcfg\.set\((?P<json>(?:\"[^\"]*\"|'[^']*'|[^()])*)\)"
YTINITIALDATA_PATTERN = r"ytInitialData = (?P<json>{.*?});"


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


@dataclass
class VideoDescription:
    video_id: str
    title: str


class VideoData(UserDict):
    @classmethod
    def from_json(cls, text: str) -> Self:
        return cls(json.loads(text))

    def iter_videos(
        self, selector: Literal["videoRenderer", "reelItemRenderer"] = "videoRenderer"
    ) -> Iterator[VideoDescription]:
        for item in json_iter(f"$..{selector}", self.data):
            yield VideoDescription(
                video_id=json_first("$.videoId", item, str),
                title=json_first("$.title.runs[0].text", item, str),
            )

    @property
    def continuation_token(self) -> str | None:
        return next(json_iter("$..continuationCommand.token", self.data, str), None)

    @property
    def click_tracking_params(self) -> str:
        return json_first("$..clickTrackingParams", self.data, str)


@dataclass
class YoutubeWebPage:
    response: Response

    def __post_init__(self):
        self.response.raise_for_status()

    @cached_property
    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.response.text, features="html.parser")

    @cached_property
    def metadata(self) -> Dict[str, str]:
        return html_get_metadata(self.response.text)

    @property
    def metadata_title(self) -> str:
        return self.metadata["og:title"]

    @property
    def metadata_avatar_url(self) -> str | None:
        return self.metadata.get("og:image")

    @property
    def metadata_url(self) -> ParseResult:
        home_url = self.metadata["og:url"]
        out = urlparse(home_url)
        assert out.hostname in ALLOWED_HOSTS, f"Not a valid youtube url: {home_url}"
        return out

    @property
    def metadata_channel_id(self) -> str:
        last_segment = self.metadata_url.path.split("/")[-1]
        assert is_channel_id(last_segment), f"Invalid channel_id: {last_segment}"
        return last_segment

    def iter_scripts(self) -> Iterator[str]:
        for script in self.soup.find_all("script"):
            if script.string is not None:
                yield script.string

    def find_initial_video_data(self) -> VideoData | None:
        for script in self.iter_scripts():
            if (m := re.search(YTINITIALDATA_PATTERN, script, re.DOTALL)) is not None:
                return VideoData.from_json(m.group("json"))

    def find_client_data(self) -> Dict[str, Any] | None:
        for script in self.iter_scripts():
            if (
                "INNERTUBE_CONTEXT" in script
                and (m := re.search(YTCFG_PATTERN, script, re.DOTALL)) is not None
            ):
                payload = json.loads(m.group("json"))
                return json_first("$.INNERTUBE_CONTEXT.client", payload)
