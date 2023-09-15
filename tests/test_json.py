from datetime import datetime
from xml.etree import ElementTree

from yourss.model import RssFeed
from yourss.schema import Feed

from .test_xml import SAMPLES_FOLDER


def test_feed():
    xmlfile = SAMPLES_FOLDER / "@jonnygiger.xml"
    assert xmlfile.exists()

    rss = RssFeed(ElementTree.fromstring(xmlfile.read_text()))
    feed = Feed.model_validate(rss)

    assert feed.title == "Jonny Giger"
    assert feed.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert str(feed.link) == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert len(feed.entries) == 15

    entry = feed.entries[0]

    assert entry.title == "HASLAM FLIP #skateboarding #skate"
    assert entry.description is not None and len(entry.description) == 21
    assert entry.published == datetime.fromisoformat("2023-09-13T18:09:30+00:00")
    assert entry.updated == datetime.fromisoformat("2023-09-13T20:05:28+00:00")
    assert entry.video_id == "7cNpRIurrkI"
    assert (
        str(entry.thumbnail_url) == "https://i4.ytimg.com/vi/7cNpRIurrkI/hqdefault.jpg"
    )
