from datetime import datetime
from pathlib import Path

from httpx import Client
from pytest import mark

from yourss.youtube import Feed

SAMPLES_FOLDER = Path(__file__).parent / "data"
FEEDS_FILE = Path(__file__).parent / "feeds.txt"


def test_feed_channel_xml() -> None:
    xmlfile = SAMPLES_FOLDER / "UCVooVnzQxPSTXTMzSi1s6uw.xml"
    assert xmlfile.exists()

    rss = Feed.from_xml(xmlfile.read_text())
    assert rss.title == "Jonny Giger"
    assert rss.uid == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert str(rss.get_url()) == "http://www.youtube.com/feeds/videos.xml?channel_id=UCVooVnzQxPSTXTMzSi1s6uw"
    assert str(rss.get_link()) == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert len(rss.entries) == 15

    for entry in rss.entries:
        assert len(entry.title) > 0
        assert entry.published > datetime.fromisoformat("2020-01-01T00:00:00+00:00")
        assert entry.updated > datetime.fromisoformat("2020-01-01T00:00:00+00:00")
        assert entry.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
        assert str(entry.media_info.thumbnail.url).endswith(".jpg")

    entry = rss.entries[0]
    assert entry.title == "IMPOSSIBLE TRICKS OF DAEWON SONG"
    assert len(entry.media_info.description) == 796
    assert entry.video_id == "dfxLY1EayNA"
    assert str(entry.media_info.thumbnail.url) == "https://i1.ytimg.com/vi/dfxLY1EayNA/hqdefault.jpg"


def test_feed_playlist_xml() -> None:
    xmlfile = SAMPLES_FOLDER / "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk.xml"
    assert xmlfile.exists()

    rss = Feed.from_xml(xmlfile.read_text())
    assert rss.title == "IMPOSSIBLE TRICKS OF RODNEY MULLEN"
    assert rss.uid == "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"
    assert rss.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert (
        str(rss.get_url()) == "http://www.youtube.com/feeds/videos.xml?playlist_id=PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"
    )
    assert len(rss.entries) == 15

    entry = rss.entries[0]
    assert entry.title == "Impossible Truckstand Of Rodney Mullen"
    assert len(entry.media_info.description) == 504
    assert entry.published == datetime.fromisoformat("2022-03-12T16:00:21+00:00")
    assert entry.updated == datetime.fromisoformat("2023-06-08T23:26:41+00:00")
    assert entry.video_id == "Ol_D2iPR9so"
    assert entry.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert str(entry.media_info.thumbnail.url) == "https://i4.ytimg.com/vi/Ol_D2iPR9so/hqdefault.jpg"


@mark.skipif(not FEEDS_FILE.exists(), reason="Missing feeds urls")
def test_multiple_feeds() -> None:
    client = Client(timeout=5)
    count = 0
    for url in FEEDS_FILE.read_text().splitlines():
        count += 1
        resp = client.get(url)
        assert resp.status_code == 200
        feed = Feed.from_xml(resp.content)
        assert feed.title is not None
        assert feed.channel_id is not None
        assert feed.channel_id.startswith("UC")
        assert feed.uid.startswith("UC"), f"{feed.title}"

    assert count > 0


def test_feed_entry_to_video() -> None:
    from yourss.youtube import ChannelDescription

    rss = Feed.from_xml((SAMPLES_FOLDER / "UCVooVnzQxPSTXTMzSi1s6uw.xml").read_text())
    entry = rss.entries[0]
    channel = ChannelDescription(channel_id=entry.channel_id, name="Jonny Giger")

    video = entry.to_video(channel)
    assert video.video_id == entry.video_id
    assert video.title == entry.title
    assert video.published_at == entry.published
    assert video.published_text is None
    assert isinstance(video.views, int) and video.views > 0
    assert video.thumbnail.startswith("https://")
    assert video.channel == channel
    # Unknown links: no avatar, and the page of the channel on Youtube derived from its id
    assert channel.avatar == ""
    assert channel.home == f"https://www.youtube.com/channel/{entry.channel_id}"
    assert entry.to_video().channel is None
