from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator


class ChannelDescription(BaseModel, frozen=True):
    channel_id: str
    name: str
    # Empty when unknown: the templates then show the initial of the channel
    avatar: str = ""
    # Its page on Youtube, derived from the id when not given
    home: str = ""
    # "@name", empty when unknown (a channel only known through its feed)
    handle: str = ""

    @model_validator(mode="before")
    @classmethod
    def _default_home(cls, data: Any) -> Any:
        if isinstance(data, dict) and "channel_id" in data and not data.get("home"):
            data = {**data, "home": f"https://www.youtube.com/channel/{data['channel_id']}"}
        return data


class VideoDescription(BaseModel, frozen=True):
    """
    A video as the templates display it, whatever its source. RSS gives exact
    values (``published_at``, ``views``); a scraped page only gives the texts
    Youtube displays (``published_text``, ``views_text``).
    """

    video_id: str
    title: str
    thumbnail: str = ""
    short: bool = False
    channel: ChannelDescription | None = None
    published_at: datetime | None = None
    published_text: str | None = None
    views: int | None = None
    views_text: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_thumbnail(cls, data: Any) -> Any:
        if isinstance(data, dict) and "video_id" in data and not data.get("thumbnail"):
            data = {
                **data,
                "thumbnail": f"https://i.ytimg.com/vi/{data['video_id']}/hqdefault.jpg",
            }
        return data
