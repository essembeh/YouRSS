from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import HttpUrl
from pydantic_xml import BaseXmlModel, attr, element


class AtomXmlModel(
    BaseXmlModel,
    nsmap={
        "": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    },
    search_mode="unordered",
): ...


class Link(AtomXmlModel):
    rel: str | None = attr(default=None)
    href: HttpUrl = attr()


class FeedAuthor(AtomXmlModel):
    name: str = element()
    uri: HttpUrl = element()


class MediaThumbnail(AtomXmlModel, ns="media"):
    url: HttpUrl = attr()
    width: int = attr()
    height: int = attr()


class MediaGroup(AtomXmlModel, ns="media"):
    title: str = element()
    thumbnail: MediaThumbnail = element()
    description: str = element(default="")


class Entry(AtomXmlModel):
    id: str = element()
    video_id: str = element(tag="videoId", ns="yt")
    channel_id: str = element(tag="channelId", ns="yt")
    title: str = element()
    links: list[Link] = element(tag="link")
    author: FeedAuthor = element()
    published: datetime = element()
    updated: datetime = element()
    media_info: MediaGroup = element(tag="group")


class Feed(AtomXmlModel, tag="feed"):
    id: str = element()
    channel_id_orig: str | None = element(tag="channelId", ns="yt", default=None)
    playlist_id: str | None = element(tag="playlistId", ns="yt", default=None)
    title: str = element()
    author: FeedAuthor = element()
    published: datetime = element()
    links: list[Link] = element(tag="link")
    entries: List[Entry] = element(tag="entry")

    def _find_link(self, rel: str) -> HttpUrl | None:
        for link in self.links:
            if link.rel == rel:
                return link.href

    def get_url(self) -> HttpUrl | None:
        return self._find_link("self")

    def get_link(self) -> HttpUrl | None:
        return self._find_link("alternate")

    @property
    def channel_id(self) -> str | None:
        return (
            f"UC{self.channel_id_orig}"
            if self.channel_id_orig is not None
            and not self.channel_id_orig.startswith("UC")
            else self.channel_id_orig
        )

    @property
    def uid(self) -> str:
        if self.playlist_id is not None:
            return self.playlist_id

        if self.channel_id is not None:
            return self.channel_id

        if (url := self.get_url()) is not None:
            for key, value in url.query_params():
                if key == "channel_id":
                    return value

        for entry in self.entries:
            if entry.channel_id is not None:
                return entry.channel_id

        return str(hash(self))
