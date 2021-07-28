from dataclasses import dataclass
from datetime import datetime
from functools import total_ordering

import requests
from lxml import etree

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def https(url):
    return url.replace("http:", "https:") if isinstance(url, str) else url


@dataclass
@total_ordering
class RssEntry:
    _root: etree.Element

    @property
    def title(self):
        out = self._root.xpath("./atom:title/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def description(self):
        out = self._root.xpath(
            "./media:group/media:description/text()", namespaces=NAMESPACES
        )
        return out[0] if len(out) else None

    @property
    def link(self):
        out = self._root.xpath(
            "./atom:link[@rel='alternate']/@href", namespaces=NAMESPACES
        )
        return out[0] if len(out) else None

    @property
    def published(self):
        out = self._root.xpath("./atom:published/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def published_date(self):
        return datetime.fromisoformat(self.published)

    @property
    def updated(self):
        out = self._root.xpath("./atom:updated/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def updated_date(self):
        return datetime.fromisoformat(self.updated)

    @property
    def video_id(self):
        out = self._root.xpath("./yt:videoId/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def channel_id(self):
        out = self._root.xpath("./yt:channelId/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def thumbnail_url(self):
        out = self._root.xpath(
            "./media:group/media:thumbnail/@url", namespaces=NAMESPACES
        )
        return out[0] if len(out) else None

    def __hash__(self):
        return hash(self._root)

    def __eq__(self, other):
        return isinstance(other, RssEntry) and self.updated_date == other.updated_date

    def __lt__(self, other):
        return isinstance(other, RssEntry) and self.updated_date < other.updated_date


@dataclass
class RssFeed:
    _root: etree.Element

    @classmethod
    def fromurl(cls, url: str):
        req = requests.get(url)
        if req.ok:
            return cls.fromstring(req.content)

    @classmethod
    def fromstring(cls, text: str):
        return cls(etree.fromstring(text))

    @property
    def title(self):
        out = self._root.xpath("./atom:title/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def channel_id(self):
        out = self._root.xpath("./yt:channelId/text()", namespaces=NAMESPACES)
        return out[0] if len(out) else None

    @property
    def url(self):
        out = self._root.xpath("./atom:link[@rel='self']/@href", namespaces=NAMESPACES)
        return https(out[0]) if len(out) else None

    @property
    def link(self):
        out = self._root.xpath(
            "./atom:link[@rel='alternate']/@href", namespaces=NAMESPACES
        )
        return out[0] if len(out) else None

    @property
    def entries(self):
        return list(
            map(
                RssEntry,
                self._root.xpath("./atom:entry", namespaces=NAMESPACES),
            )
        )

    def __hash__(self):
        return hash(self._root)
