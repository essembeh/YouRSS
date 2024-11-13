import json
from collections import UserDict
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Literal, Self
from urllib.parse import urlparse

from .utils import is_channel_id, json_first, json_iter

ALLOWED_HOSTS = ["consent.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"]


class YoutubeMetadata(UserDict[str, str]):
    @property
    def title(self) -> str:
        return self["og:title"]

    @property
    def avatar_url(self) -> str | None:
        return self.get("og:image")

    @property
    def url(self) -> str:
        return self["og:url"]

    @property
    def channel_id(self) -> str:
        url = urlparse(self.url)
        assert url.hostname in ALLOWED_HOSTS, f"Not a valid youtube url: {self.url}"
        last_segment = url.path.split("/")[-1]
        assert is_channel_id(last_segment), f"Invalid channel_id: {last_segment}"
        return last_segment


@dataclass
class VideoDescription:
    video_id: str
    title: str
    published: str

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> Self:
        return cls(
            video_id=json_first("$.videoId", payload, str),
            title=json_first("$.title.runs[0].text", payload, str),
            published=json_first("$.publishedTimeText.simpleText", payload, str),
        )


class BrowseData(UserDict[str, Any]):
    @classmethod
    def from_json_string(cls, text: str) -> Self:
        return cls(json.loads(text))

    def iter_videos(
        self, selector: Literal["videoRenderer", "reelItemRenderer"] = "videoRenderer"
    ) -> Iterator[VideoDescription]:
        for item in json_iter(f"$..{selector}", self.data):
            yield VideoDescription.from_json(item)

    @property
    def continuation_token(self) -> str | None:
        return next(json_iter("$..continuationCommand.token", self.data, str), None)

    @property
    def click_tracking_params(self) -> str:
        return json_first("$..clickTrackingParams", self.data, str)
