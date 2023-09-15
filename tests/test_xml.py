from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from yourss.model import RssFeed

SAMPLES_FOLDER = Path(__file__).parent.parent / "samples"


def test_xml():
    xmlfile = SAMPLES_FOLDER / "@jonnygiger.xml"
    assert xmlfile.exists()

    rss = RssFeed(ElementTree.fromstring(xmlfile.read_text()))
    assert rss.title == "Jonny Giger"
    assert rss.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert (
        rss.url
        == "https://www.youtube.com/feeds/videos.xml?channel_id=UCVooVnzQxPSTXTMzSi1s6uw"
    )
    assert rss.link == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert len(rss.entries) == 15

    entry = rss.entries[0]
    assert entry.title == "HASLAM FLIP #skateboarding #skate"
    assert len(entry.description) == 21
    assert entry.published == "2023-09-13T18:09:30+00:00"
    assert entry.published_date == datetime.fromisoformat("2023-09-13T18:09:30+00:00")
    assert entry.updated == "2023-09-13T20:05:28+00:00"
    assert entry.updated_date == datetime.fromisoformat("2023-09-13T20:05:28+00:00")
    assert entry.video_id == "7cNpRIurrkI"
    assert entry.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert entry.thumbnail_url == "https://i4.ytimg.com/vi/7cNpRIurrkI/hqdefault.jpg"
