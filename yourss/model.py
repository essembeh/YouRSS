from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import total_ordering
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import arrow
from httpx import Response

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def https(url: str) -> str:
    return url.replace("http:", "https:") if isinstance(url, str) else url


def checknode(element: ElementTree.Element | None) -> ElementTree.Element:
    assert element is not None
    return element


def checknodetext(element: ElementTree.Element | None) -> str:
    element = checknode(element)
    assert element.text is not None
    return element.text


def checknodeattr(element: ElementTree.Element | None, key: str) -> str:
    element = checknode(element)
    return element.attrib[key]


@dataclass
@total_ordering
class RssEntry:
    root: ElementTree.Element

    @property
    def title(self) -> str:
        return checknodetext(self.root.find("./atom:title", namespaces=NAMESPACES))

    @property
    def description(self) -> str | None:
        node = checknode(
            self.root.find("./media:group/media:description", namespaces=NAMESPACES)
        )
        return node.text

    @property
    def link(self) -> str:
        return checknodeattr(
            self.root.find("./atom:link[@rel='alternate']", namespaces=NAMESPACES),
            "href",
        )

    @property
    def published(self) -> str:
        return checknodetext(self.root.find("./atom:published", namespaces=NAMESPACES))

    @property
    def published_date(self) -> datetime:
        return datetime.fromisoformat(self.published)

    @property
    def published_moment(self) -> str:
        date = arrow.get(self.published)
        return date.humanize()

    @property
    def updated(self) -> str:
        return checknodetext(self.root.find("./atom:updated", namespaces=NAMESPACES))

    @property
    def updated_date(self) -> datetime:
        return datetime.fromisoformat(self.updated)

    @property
    def updated_moment(self) -> str:
        date = arrow.get(self.updated)
        return date.humanize()

    @property
    def video_id(self) -> str:
        return checknodetext(self.root.find("./yt:videoId", namespaces=NAMESPACES))

    @property
    def channel_id(self) -> str:
        return checknodetext(self.root.find("./yt:channelId", namespaces=NAMESPACES))

    @property
    def thumbnail_url(self) -> str:
        return checknodeattr(
            self.root.find("./media:group/media:thumbnail", namespaces=NAMESPACES),
            "url",
        )

    def __hash__(self):
        return hash(self.root)

    def __eq__(self, other):
        return isinstance(other, RssEntry) and self.updated_date == other.updated_date

    def __lt__(self, other):
        return isinstance(other, RssEntry) and self.updated_date < other.updated_date


@dataclass
class RssFeed:
    root: ElementTree.Element

    @classmethod
    def fromresponse(cls, resp: Response) -> RssFeed:
        resp.raise_for_status()
        return cls.fromstring(resp.text)

    @classmethod
    def fromstring(cls, text: str) -> RssFeed:
        out = cls(ElementTree.fromstring(text))
        assert out.title is not None
        return out

    @property
    def title(self) -> str:
        return checknodetext(self.root.find("./atom:title", namespaces=NAMESPACES))

    @property
    def channel_id(self) -> str:
        node = checknode(self.root.find("./yt:channelId", namespaces=NAMESPACES))
        if (out := node.text) is not None:
            # workaround, sometime channel id does not start with UC
            if out.startswith("UC"):
                return out
        # no channel id, parse the url to retrieve it
        params = parse_qs(urlparse(self.url).query)
        channel_id = params.get("channel_id")
        assert channel_id is not None and len(channel_id) > 0
        return channel_id[0]

    @property
    def url(self) -> str:
        return https(
            checknodeattr(
                self.root.find("./atom:link[@rel='self']", namespaces=NAMESPACES),
                "href",
            )
        )

    @property
    def link(self) -> str | None:
        node = self.root.find("./atom:link[@rel='alternate']", namespaces=NAMESPACES)
        return checknodeattr(node, "href") if node is not None else None

    @property
    def entries(self) -> list[RssEntry]:
        return [
            RssEntry(e)
            for e in self.root.findall("./atom:entry", namespaces=NAMESPACES)
        ]
