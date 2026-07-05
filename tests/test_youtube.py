import pytest
from bs4 import BeautifulSoup
from httpx import get

from yourss.youtube import YoutubeApi
from yourss.youtube.parser import (
    SHORTS_PARSERS,
    VIDEO_PARSERS,
    ScrapingError,
    parse_items,
)

CHANNEL = "UCVooVnzQxPSTXTMzSi1s6uw"


def is_rgpd_applicable():
    resp = get("https://ifconfig.io/country_code")
    return resp.status_code == 200 and resp.text.strip() == "FR"


@pytest.mark.skipif(not is_rgpd_applicable(), reason="Not applicable outside Europe")
@pytest.mark.asyncio(loop_scope="module")
async def test_rgpd():
    api = YoutubeApi()

    url = "/@jonnygiger"

    resp = await api.get_html(url)
    assert resp.status_code == 200
    assert (
        len(
            BeautifulSoup(resp.text, features="html.parser").find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
        )
        == 0
    )

    resp = await api.get_html(url, ucbcb=0)
    assert resp.status_code == 200
    assert (
        len(
            BeautifulSoup(resp.text, features="html.parser").find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
        )
        > 0
    )


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_channel():
    api = YoutubeApi()

    feed = await api.get_channel_rss("UCVooVnzQxPSTXTMzSi1s6uw")
    assert feed.title == "Jonny Giger"


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_playlist():
    api = YoutubeApi()

    feed = await api.get_playlist_rss("PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk")
    assert feed.title == "IMPOSSIBLE TRICKS OF RODNEY MULLEN"


@pytest.mark.asyncio(loop_scope="module")
async def test_metadata_channel():
    api = YoutubeApi()

    page = await api.get_homepage("UCVooVnzQxPSTXTMzSi1s6uw")
    channel = page.get_metadata()
    assert channel.name == "Jonny Giger"
    assert channel.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.home == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.avatar is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_metadata_user():
    api = YoutubeApi()

    page = await api.get_homepage("@jonnygiger")
    channel = page.get_metadata()
    assert channel.name == "Jonny Giger"
    assert channel.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.home == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.avatar is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_videos():
    api = YoutubeApi()

    page_iterator = api.iter_videos(CHANNEL)
    page1 = await anext(page_iterator)
    assert len(page1) == 30
    page2 = await anext(page_iterator)
    assert len(page2) > 10
    assert page1 != page2


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_videos_fields():
    api = YoutubeApi()

    homepage = await api.get_homepage(CHANNEL, suffix="/videos")
    browse_data = homepage.find_browse_data()
    assert browse_data is not None

    videos = list(browse_data.iter_videos())
    assert len(videos) == 30
    for video in videos:
        assert video.video_id
        assert video.title
        assert video.published
        assert video.thumbnail


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_shorts():
    api = YoutubeApi()

    homepage = await api.get_homepage(CHANNEL, suffix="/shorts")
    browse_data = homepage.find_browse_data()
    assert browse_data is not None

    shorts = list(browse_data.iter_videos(shorts=True))
    assert len(shorts) > 10
    for short in shorts:
        assert short.video_id
        assert short.title
        assert short.thumbnail


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_streams():
    api = YoutubeApi()

    homepage = await api.get_homepage(CHANNEL, suffix="/streams")
    browse_data = homepage.find_browse_data()
    assert browse_data is not None

    streams = list(browse_data.iter_videos())
    assert len(streams) > 0
    for stream in streams:
        assert stream.video_id
        assert stream.title
        assert stream.thumbnail


def test_date_humanize_handles_none():
    # A missing publish date must render as empty, never crash the template.
    from yourss.routers.jinja import date_humanize

    assert date_humanize(None) == ""
    assert date_humanize("4 weeks ago") == "4 weeks ago"


def test_parser_empty_payload_returns_empty():
    # A payload with no video-like node should yield nothing, not raise.
    assert parse_items({"foo": "bar"}, VIDEO_PARSERS) == []
    assert parse_items({"foo": "bar"}, SHORTS_PARSERS) == []


def test_parser_detects_breakage():
    # A payload that clearly holds video nodes but in an unknown shape must
    # raise ScrapingError instead of silently returning an empty list.
    broken = {"videoRenderer": {"unexpectedField": "no videoId here"}}
    with pytest.raises(ScrapingError):
        parse_items(broken, VIDEO_PARSERS)


def test_parser_legacy_video_fallback():
    # Legacy videoRenderer payloads must still parse via the fallback parser.
    legacy = {
        "videoRenderer": {
            "videoId": "abc12345678",
            "title": {"runs": [{"text": "Legacy title"}]},
            "publishedTimeText": {"simpleText": "2 days ago"},
            "thumbnail": {"thumbnails": [{"url": "https://i.ytimg.com/x.jpg?foo=1"}]},
        }
    }
    items = parse_items(legacy, VIDEO_PARSERS)
    assert items == [
        {
            "video_id": "abc12345678",
            "title": "Legacy title",
            "published": "2 days ago",
            "thumbnail": "https://i.ytimg.com/x.jpg",
        }
    ]


def test_parser_lockup_video():
    # Minimal reproduction of the current lockupViewModel video shape.
    lockup = {
        "lockupViewModel": {
            "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
            "contentId": "abc12345678",
            "contentImage": {
                "thumbnailViewModel": {
                    "image": {"sources": [{"url": "https://i.ytimg.com/x.jpg?foo=1"}]}
                }
            },
            "metadata": {
                "lockupMetadataViewModel": {
                    "title": {"content": "New title"},
                    "metadata": {
                        "contentMetadataViewModel": {
                            "metadataRows": [
                                {
                                    "metadataParts": [
                                        {"text": {"content": "90K views"}},
                                        {
                                            "text": {"content": "4 weeks ago"},
                                            "accessibilityLabel": "4 weeks ago",
                                        },
                                    ]
                                }
                            ]
                        }
                    },
                }
            },
        }
    }
    items = parse_items(lockup, VIDEO_PARSERS)
    assert items == [
        {
            "video_id": "abc12345678",
            "title": "New title",
            "published": "4 weeks ago",
            "thumbnail": "https://i.ytimg.com/x.jpg",
        }
    ]


def _lockup_with_rows(rows):
    return {
        "lockupViewModel": {
            "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
            "contentId": "abc12345678",
            "metadata": {
                "lockupMetadataViewModel": {
                    "title": {"content": "T"},
                    "metadata": {"contentMetadataViewModel": {"metadataRows": rows}},
                }
            },
        }
    }


def test_parser_published_compact_with_icon():
    # Compact layout: the view counter carries a leadingIcon AND a "views"
    # accessibility label, the date carries its own label. Must pick the date.
    rows = [
        {
            "metadataParts": [
                {
                    "text": {"content": "1.1M"},
                    "accessibilityLabel": "1.1 million views",
                    "leadingIcon": {"name": "PLAY_ARROW_OUTLINED"},
                },
                {"text": {"content": "21h ago"}, "accessibilityLabel": "21 hours ago"},
            ]
        }
    ]
    [item] = parse_items(_lockup_with_rows(rows), VIDEO_PARSERS)
    assert item["published"] == "21 hours ago"


def test_parser_published_members_only():
    # Members-only video: a single date part (no view counter) plus a badge row.
    rows = [
        {
            "metadataParts": [
                {"text": {"content": "2 days ago"}, "accessibilityLabel": "2 days ago"}
            ]
        },
        {"badges": [{"badgeViewModel": {"badgeText": "Members only"}}]},
    ]
    [item] = parse_items(_lockup_with_rows(rows), VIDEO_PARSERS)
    assert item["published"] == "2 days ago"


def test_parser_published_missing_is_none():
    # No date part at all (e.g. only a view counter) must yield None, not crash.
    rows = [
        {
            "metadataParts": [
                {
                    "text": {"content": "1.1M"},
                    "accessibilityLabel": "1.1 million views",
                    "leadingIcon": {"name": "PLAY_ARROW_OUTLINED"},
                }
            ]
        }
    ]
    [item] = parse_items(_lockup_with_rows(rows), VIDEO_PARSERS)
    assert item["published"] is None


def test_parser_legacy_shorts_fallback():
    # Legacy richItemRenderer shorts must still parse via the fallback parser.
    legacy = {
        "richItemRenderer": {
            "content": {
                "reelItemRenderer": {
                    "reelWatchEndpoint": {"videoId": "abc12345678"},
                    "headline": {
                        "primaryText": {"content": "Old short"},
                        "secondaryText": {"content": "10K views"},
                    },
                    "thumbnail": {
                        "sources": [{"url": "https://i.ytimg.com/s.jpg?a=1"}]
                    },
                }
            }
        }
    }
    items = parse_items(legacy, SHORTS_PARSERS)
    assert items == [
        {
            "video_id": "abc12345678",
            "title": "Old short",
            "published": "10K views",
            "thumbnail": "https://i.ytimg.com/s.jpg",
        }
    ]


def test_parser_shorts_lockup():
    # Minimal reproduction of the current shortsLockupViewModel shape.
    shorts = {
        "shortsLockupViewModel": {
            "entityId": "shorts-shelf-item-abc12345678",
            "overlayMetadata": {
                "primaryText": {"content": "Short title"},
                "secondaryText": {"content": "532K views"},
            },
            "thumbnailViewModel": {
                "image": {"sources": [{"url": "https://i.ytimg.com/s.jpg?bar=2"}]}
            },
            "onTap": {
                "innertubeCommand": {"reelWatchEndpoint": {"videoId": "abc12345678"}}
            },
        }
    }
    items = parse_items(shorts, SHORTS_PARSERS)
    assert items == [
        {
            "video_id": "abc12345678",
            "title": "Short title",
            "published": "532K views",
            "thumbnail": "https://i.ytimg.com/s.jpg",
        }
    ]
