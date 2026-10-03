from typing import Any

import pytest
from bs4 import BeautifulSoup
from httpx import get

from yourss.youtube import ScrapingError, YoutubeApi
from yourss.youtube.cache import channel_cache
from yourss.youtube.scraping.items import SHORTS_PARSERS, VIDEO_PARSERS, parse_items

CHANNEL = "UCVooVnzQxPSTXTMzSi1s6uw"
# @thinkerview streams its interviews
STREAMING_CHANNEL = "UCQgWpmt02UtJkyO32HGUASQ"


def is_rgpd_applicable() -> bool:
    resp = get("https://ifconfig.io/country_code")
    return resp.status_code == 200 and resp.text.strip() == "FR"


@pytest.mark.skipif(not is_rgpd_applicable(), reason="Not applicable outside Europe")
@pytest.mark.asyncio(loop_scope="module")
async def test_rgpd() -> None:
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
async def test_rss_channel() -> None:
    api = YoutubeApi()

    feed = await api.get_channel_rss("UCVooVnzQxPSTXTMzSi1s6uw")
    assert feed.title == "Jonny Giger"


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_playlist() -> None:
    api = YoutubeApi()

    feed = await api.get_playlist_rss("PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk")
    assert feed.title == "IMPOSSIBLE TRICKS OF RODNEY MULLEN"


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("name", [CHANNEL, "@jonnygiger"])
async def test_channel_page(name: str) -> None:
    api = YoutubeApi()

    page = await api.get_channel_page(name)
    assert page.channel.name == "Jonny Giger"
    assert page.channel.channel_id == CHANNEL
    assert page.channel.home == f"https://www.youtube.com/channel/{CHANNEL}"
    assert page.channel.avatar is not None
    assert page.selected_tab is None
    # This channel publishes videos and shorts but no live stream
    assert page.tabs == ["videos", "shorts"]


@pytest.mark.asyncio(loop_scope="module")
async def test_channel_cached() -> None:
    api = YoutubeApi()
    channel_cache.clear()

    channel = await api.get_channel("@JonnyGiger")
    assert channel.channel_id == CHANNEL
    # Known under the handle (case insensitive) and under the channel id
    assert channel_cache.get("@jonnygiger") == channel
    assert channel_cache.get(CHANNEL) == channel
    assert await api.get_channel(CHANNEL) is channel


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_videos() -> None:
    api = YoutubeApi()

    page_iterator = api.iter_videos(CHANNEL)
    page1 = await anext(page_iterator)
    assert len(page1) == 30
    page2 = await anext(page_iterator)
    assert len(page2) > 10
    assert page1 != page2


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_videos_fields() -> None:
    api = YoutubeApi()

    page = await api.get_channel_page(CHANNEL, "videos")
    assert page.selected_tab == "videos"

    videos = page.videos()
    assert videos.continuation is not None
    assert len(videos.videos) == 30
    for video in videos.videos:
        assert video.video_id
        assert video.title
        assert video.published_text
        assert video.views_text
        assert video.published_at is None
        assert not video.short
        assert video.thumbnail


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_shorts() -> None:
    api = YoutubeApi()

    page = await api.get_channel_page(CHANNEL, "shorts")
    assert page.selected_tab == "shorts"

    shorts = page.videos(shorts=True).videos
    assert len(shorts) > 10
    for short in shorts:
        assert short.short
        assert short.views_text
        assert short.video_id
        assert short.title
        assert short.thumbnail


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_streams() -> None:
    api = YoutubeApi()

    page = await api.get_channel_page(STREAMING_CHANNEL, "streams")
    assert page.selected_tab == "streams"

    streams = page.videos().videos
    assert len(streams) > 0
    for stream in streams:
        assert stream.video_id
        assert stream.title
        assert stream.thumbnail


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_missing_tab() -> None:
    api = YoutubeApi()

    # Youtube serves the channel home when the tab does not exist
    page = await api.get_channel_page(CHANNEL, "streams")
    assert page.selected_tab is None
    assert "streams" not in page.tabs


def test_date_humanize_handles_none() -> None:
    # A missing publish date must render as empty, never crash the template.
    from yourss.routers.jinja import date_humanize

    assert date_humanize(None) == ""
    assert date_humanize("4 weeks ago") == "4 weeks ago"


def test_parser_empty_payload_returns_empty() -> None:
    # A payload with no video-like node should yield nothing, not raise.
    assert parse_items({"foo": "bar"}, VIDEO_PARSERS) == []
    assert parse_items({"foo": "bar"}, SHORTS_PARSERS) == []


def test_parser_detects_breakage() -> None:
    # A payload that clearly holds video nodes but in an unknown shape must
    # raise ScrapingError instead of silently returning an empty list.
    broken = {"videoRenderer": {"unexpectedField": "no videoId here"}}
    with pytest.raises(ScrapingError):
        parse_items(broken, VIDEO_PARSERS)


def test_parser_legacy_video_fallback() -> None:
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
            "published_text": "2 days ago",
            "views_text": None,
            "thumbnail": "https://i.ytimg.com/x.jpg",
        }
    ]


def test_parser_lockup_video() -> None:
    # Minimal reproduction of the current lockupViewModel video shape.
    lockup = {
        "lockupViewModel": {
            "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
            "contentId": "abc12345678",
            "contentImage": {
                "thumbnailViewModel": {"image": {"sources": [{"url": "https://i.ytimg.com/x.jpg?foo=1"}]}}
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
            "published_text": "4 weeks ago",
            "views_text": "90K views",
            "thumbnail": "https://i.ytimg.com/x.jpg",
        }
    ]


def _lockup_with_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
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


def test_parser_published_compact_with_icon() -> None:
    # Compact layout: the view counter carries a leadingIcon AND a "views"
    # accessibility label, the date carries its own label. Must pick the date.
    rows: list[dict[str, Any]] = [
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
    assert item["published_text"] == "21 hours ago"
    assert item["views_text"] == "1.1 million views"


def test_parser_published_members_only() -> None:
    # Members-only video: a single date part (no view counter) plus a badge row.
    rows: list[dict[str, Any]] = [
        {"metadataParts": [{"text": {"content": "2 days ago"}, "accessibilityLabel": "2 days ago"}]},
        {"badges": [{"badgeViewModel": {"badgeText": "Members only"}}]},
    ]
    [item] = parse_items(_lockup_with_rows(rows), VIDEO_PARSERS)
    assert item["published_text"] == "2 days ago"
    assert item["views_text"] is None


def test_parser_published_missing_is_none() -> None:
    # No date part at all (e.g. only a view counter) must yield None, not crash.
    rows: list[dict[str, Any]] = [
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
    assert item["published_text"] is None


def test_parser_legacy_shorts_fallback() -> None:
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
                    "thumbnail": {"sources": [{"url": "https://i.ytimg.com/s.jpg?a=1"}]},
                }
            }
        }
    }
    items = parse_items(legacy, SHORTS_PARSERS)
    assert items == [
        {
            "video_id": "abc12345678",
            "title": "Old short",
            "views_text": "10K views",
            "thumbnail": "https://i.ytimg.com/s.jpg",
            "short": True,
        }
    ]


def test_parser_shorts_lockup() -> None:
    # Minimal reproduction of the current shortsLockupViewModel shape.
    shorts = {
        "shortsLockupViewModel": {
            "entityId": "shorts-shelf-item-abc12345678",
            "overlayMetadata": {
                "primaryText": {"content": "Short title"},
                "secondaryText": {"content": "532K views"},
            },
            "thumbnailViewModel": {"image": {"sources": [{"url": "https://i.ytimg.com/s.jpg?bar=2"}]}},
            "onTap": {"innertubeCommand": {"reelWatchEndpoint": {"videoId": "abc12345678"}}},
        }
    }
    items = parse_items(shorts, SHORTS_PARSERS)
    assert items == [
        {
            "video_id": "abc12345678",
            "title": "Short title",
            "views_text": "532K views",
            "thumbnail": "https://i.ytimg.com/s.jpg",
            "short": True,
        }
    ]
