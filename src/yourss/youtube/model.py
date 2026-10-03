from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator


class ChannelDescription(BaseModel, frozen=True):
    channel_id: str
    name: str
    # Absolute Youtube URLs when known, else application routes which resolve them on demand
    avatar: str = ""
    home: str = ""
    # "@name", empty when unknown (a channel only known through its feed)
    handle: str = ""

    @model_validator(mode="before")
    @classmethod
    def _default_links(cls, data: Any) -> Any:
        if isinstance(data, dict) and "channel_id" in data:
            data = dict(data)
            data["avatar"] = data.get("avatar") or f"/proxy/avatar/{data['channel_id']}"
            data["home"] = data.get("home") or f"/proxy/home/{data['channel_id']}"
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
