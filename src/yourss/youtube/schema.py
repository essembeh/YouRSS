from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import HttpUrl
from pydantic_xml import BaseXmlModel, attr, element
from rapid_api_client import ResponseModel

from .model import ChannelDescription, VideoDescription
from .utils import is_channel_id


class AtomXmlModel(
    BaseXmlModel,
    ResponseModel,
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


class MediaStatistics(AtomXmlModel, ns="media"):
    views: int = attr()


class MediaCommunity(AtomXmlModel, ns="media"):
    statistics: MediaStatistics | None = element(default=None)


class MediaGroup(AtomXmlModel, ns="media"):
    title: str = element()
    thumbnail: MediaThumbnail = element()
    description: str = element(default="")
    community: MediaCommunity | None = element(default=None)


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

    @property
    def is_short(self) -> bool:
        # The link of a short points to /shorts/<id> instead of /watch?v=<id>
        return any("/shorts/" in str(link.href) for link in self.links)

    @property
    def views(self) -> int | None:
        community = self.media_info.community
        return community.statistics.views if community and community.statistics else None

    def to_video(self, channel: ChannelDescription | None = None) -> VideoDescription:
        """The only place where an RSS entry becomes a video of the application."""
        return VideoDescription(
            video_id=self.video_id,
            title=self.title,
            thumbnail=str(self.media_info.thumbnail.url),
            short=self.is_short,
            channel=channel,
            published_at=self.published,
            views=self.views,
        )


class Feed(AtomXmlModel, tag="feed"):
    id: str = element()
    channel_id_orig: str | None = element(tag="channelId", ns="yt", default=None)
    playlist_id: str | None = element(tag="playlistId", ns="yt", default=None)
    title: str = element()
    author: FeedAuthor = element()
    published: datetime = element()
    links: list[Link] = element(tag="link")
    # Youtube sometimes serves the feed of a playlist without any entry
    entries: list[Entry] = element(tag="entry", default_factory=list)

    def _find_link(self, rel: str) -> HttpUrl | None:
        for link in self.links:
            if link.rel == rel:
                return link.href
        return None

    def get_url(self) -> HttpUrl | None:
        return self._find_link("self")

    def get_link(self) -> HttpUrl | None:
        return self._find_link("alternate")

    @property
    def channel_id(self) -> str:
        if self.channel_id_orig is None:
            out = urlparse(str(self.author.uri)).path.split("/")[-1]
            if is_channel_id(out):
                return out
        else:
            out = self.channel_id_orig
            if is_channel_id(out):
                return out
            out = f"UC{out}"
            if is_channel_id(out):
                return out
        raise ValueError(f"Invalid channel_id: {out}")

    @property
    def uid(self) -> str:
        return self.playlist_id if self.playlist_id is not None else self.channel_id
