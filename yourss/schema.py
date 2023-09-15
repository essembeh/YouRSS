from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class Video(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    title: str
    description: str | None
    link: HttpUrl
    published: datetime
    updated: datetime
    thumbnail_url: HttpUrl


class Feed(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    channel_id: str
    link: HttpUrl
    entries: list[Video]
