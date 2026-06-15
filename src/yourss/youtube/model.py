import json
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator, Self

from .parser import SHORTS_PARSERS, VIDEO_PARSERS, parse_items
from .utils import find_key


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
        parsers = SHORTS_PARSERS if shorts else VIDEO_PARSERS
        for kwargs in parse_items(self.data, parsers):
            yield VideoDescription(**kwargs)

    @property
    def continuation_token(self) -> str | None:
        token = find_key("continuationCommand", self.data, dict)
        return token.get("token") if token else None

    @property
    def click_tracking_params(self) -> str | None:
        return find_key("clickTrackingParams", self.data, str)
