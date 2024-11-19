import json
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator, Self

from .utils import json_first, json_iter


@dataclass
class ChannelDescription:
    channel_id: str
    name: str
    avatar: str | None
    home: str | None

    def __post_init__(self):
        if self.avatar is None:
            self.avatar = f"/proxy/avatar/{self.channel_id}"
        if self.home is None:
            self.home = f"/proxy/home/{self.channel_id}"


@dataclass
class VideoDescription:
    video_id: str
    title: str
    published: str | datetime
    thumbnail: str | None
    channel: ChannelDescription | None = None

    def __post_init__(self):
        if self.thumbnail is None:
            self.thumbnail = f"/proxy/thumbnail/{self.video_id}"


class BrowseData(UserDict[str, Any]):
    @classmethod
    def from_json_string(cls, text: str) -> Self:
        return cls(json.loads(text))

    def iter_videos(self, shorts: bool = False) -> Iterator[VideoDescription]:
        for item in json_iter(
            "$..richItemRenderer" if shorts else "$..videoRenderer", self.data
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
                    thumbnail=json_first("$.thumbnail.thumbnails[0].url", item, str),
                )

    @property
    def continuation_token(self) -> str | None:
        return next(json_iter("$..continuationCommand.token", self.data, str), None)

    @property
    def click_tracking_params(self) -> str:
        return json_first("$..clickTrackingParams", self.data, str)
