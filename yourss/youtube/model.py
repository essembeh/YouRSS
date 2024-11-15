import json
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator, Self
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
    published: str | datetime
    channel: str | None = None
    channel_id: str | None = None
    thumbnail: str | None = None
    feed_uid: str | None = None

    def __post_init__(self):
        if self.thumbnail is None:
            self.thumbnail = f"https://i1.ytimg.com/vi/{self.video_id}/hqdefault.jpg"


class BrowseData(UserDict[str, Any]):
    @classmethod
    def from_json_string(cls, text: str) -> Self:
        return cls(json.loads(text))

    def iter_videos(self, shorts: bool = False) -> Iterator[VideoDescription]:
        for item in json_iter(
            f"$..{'videoRenderer' if not shorts else  'richItemRenderer'}", self.data
        ):
            if shorts:
                yield VideoDescription(
                    video_id=json_first(
                        "$.content..reelWatchEndpoint.videoId", item, str
                    ),
                    title=json_first("$.content..primaryText.content", item, str),
                    published=json_first("$.content..secondaryText.content", item, str),
                    thumbnail=json_first(
                        "$.content..thumbnail.sources[0].url", item, str
                    ),
                )
            else:
                yield VideoDescription(
                    video_id=json_first("$.videoId", item, str),
                    title=json_first("$.title.runs[0].text", item, str),
                    published=json_first("$.publishedTimeText.simpleText", item, str),
                )

    @property
    def continuation_token(self) -> str | None:
        return next(json_iter("$..continuationCommand.token", self.data, str), None)

    @property
    def click_tracking_params(self) -> str:
        return json_first("$..clickTrackingParams", self.data, str)
