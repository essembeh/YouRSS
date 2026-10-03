import json
import re
from datetime import timedelta

import pytest

from yourss.settings import current_config
from yourss.youtube import ChannelDescription, Continuation, ScrapingError
from yourss.youtube.cache import ChannelCache
from yourss.youtube.scraping import parse_channel_page, parse_continuation
from yourss.youtube.scraping.extract import (
    extract_client_version,
    extract_initial_data,
    extract_json,
)

CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"


def _tab(name: str, selected: bool = False) -> dict:
    url = f"/channel/{CHANNEL_ID}/{name}"
    return {
        "tabRenderer": {
            "selected": selected,
            "endpoint": {"commandMetadata": {"webCommandMetadata": {"url": url}}},
        }
    }


def _lockup(video_id: str) -> dict:
    return {
        "lockupViewModel": {
            "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
            "contentId": video_id,
            "metadata": {"lockupMetadataViewModel": {"title": {"content": f"Title {video_id}"}}},
        }
    }


def _page(data: dict, version: str | None = "2.20260101.00.00") -> str:
    config = f'<script>ytcfg.set({{"INNERTUBE_CLIENT_VERSION":"{version}"}});</script>' if version else ""
    return f"<html><head>{config}<script>var ytInitialData = {json.dumps(data)};</script></head><body>}};</body></html>"


def _channel_data(*tabs: dict, contents: list | None = None) -> dict:
    return {
        "metadata": {
            "channelMetadataRenderer": {
                "title": "Jonny Giger",
                "externalId": CHANNEL_ID,
                "channelUrl": f"https://www.youtube.com/channel/{CHANNEL_ID}",
                "avatar": {"thumbnails": [{"url": "https://yt3.googleusercontent.com/abc=s900-c-k-c0x00ffffff-no-rj"}]},
            }
        },
        "contents": {"tabs": list(tabs), "items": contents or []},
    }


def test_extract_json():
    pattern = re.compile(r"marker = (?={)")
    html = 'before marker = {"a": {"b": "};"}, "c": [1, 2]}; after'
    assert extract_json(html, pattern) == {"a": {"b": "};"}, "c": [1, 2]}
    assert extract_json(html, re.compile(r"missing = (?={)")) is None
    assert extract_json("marker = {broken", pattern) is None
    # An unreadable occurrence does not hide a readable one
    assert extract_json('marker = {broken; marker = {"ok": 1}', pattern) == {"ok": 1}


def test_extract_initial_data_variants():
    assert extract_initial_data('<script>var ytInitialData = {"a": 1};</script>') == {"a": 1}
    assert extract_initial_data('<script>window["ytInitialData"] = {"a": 2};</script>') == {"a": 2}
    json_element = (
        '<script id="yt-initial-data" type="application/json" nonce="x">{"a": 3}</script>'
        "<script>window['ytInitialData'] = JSON.parse(ytDataEl.textContent);</script>"
    )
    assert extract_initial_data(json_element) == {"a": 3}
    with pytest.raises(ScrapingError, match=r"JSON\.parse"):
        extract_initial_data("<script>var ytInitialData = JSON.parse('...');</script>")


def test_extract_client_version():
    assert extract_client_version(_page({})) == "2.20260101.00.00"
    assert extract_client_version("<html></html>") is None


def test_channel_page_metadata_and_tabs():
    page = parse_channel_page(
        _page(
            _channel_data(
                _tab("featured"),
                _tab("videos", selected=True),
                _tab("shorts"),
                _tab("playlists"),
            )
        )
    )
    assert page.channel.channel_id == CHANNEL_ID
    assert page.channel.name == "Jonny Giger"
    assert page.channel.home == f"https://www.youtube.com/channel/{CHANNEL_ID}"
    # The advertised avatar is resized to what the UI needs
    assert page.channel.avatar == "https://yt3.googleusercontent.com/abc=s176-c-k-c0x00ffffff-no-rj"
    assert page.tabs == ["videos", "shorts"]
    assert page.selected_tab == "videos"


def test_channel_page_missing_tab_falls_back_to_home():
    page = parse_channel_page(_page(_channel_data(_tab("featured", selected=True), _tab("videos"))))
    assert page.tabs == ["videos"]
    assert page.selected_tab is None


def test_channel_page_videos_and_continuation():
    contents = [
        _lockup("aaaaaaaaaaa"),
        _lockup("bbbbbbbbbbb"),
        {"continuationCommand": {"token": "TOKEN"}},
    ]
    page = parse_channel_page(_page(_channel_data(_tab("videos", selected=True), contents=contents)))
    videos = page.videos()
    assert [v.video_id for v in videos.videos] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    assert videos.videos[0].thumbnail == "https://i.ytimg.com/vi/aaaaaaaaaaa/hqdefault.jpg"
    assert videos.continuation == Continuation(token="TOKEN", client_version="2.20260101.00.00")


def test_channel_page_without_client_version_cannot_continue():
    contents = [_lockup("aaaaaaaaaaa"), {"continuationCommand": {"token": "TOKEN"}}]
    page = parse_channel_page(
        _page(
            _channel_data(_tab("videos", selected=True), contents=contents),
            version=None,
        )
    )
    assert page.videos().continuation is None


def test_channel_page_breakage_is_detected():
    with pytest.raises(ScrapingError):
        parse_channel_page("<html>no data</html>")
    with pytest.raises(ScrapingError):
        parse_channel_page(_page({"metadata": {"somethingElse": {}}}))


def test_parse_continuation():
    previous = Continuation(token="TOKEN", client_version="2.20260101.00.00")
    payload = {"items": [_lockup("ccccccccccc"), {"continuationCommand": {"token": "NEXT"}}]}
    page = parse_continuation(payload, previous)
    assert [v.video_id for v in page.videos] == ["ccccccccccc"]
    assert page.continuation == Continuation(token="NEXT", client_version="2.20260101.00.00")
    assert parse_continuation({"items": [_lockup("ddddddddddd")]}, previous).continuation is None


def _channel(index: int) -> ChannelDescription:
    return ChannelDescription(channel_id=f"UC{index:022d}", name=f"Channel {index}")


def test_channel_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(current_config, "channel_cache_ttl", timedelta(hours=1))
    cache = ChannelCache(max_size=4)
    for index in range(10):
        cache.put(f"@channel{index}", _channel(index))
    assert len(cache) == 4
    # The oldest entries were dropped, the latest one is known under both of its names
    assert cache.get("@channel0") is None
    assert cache.get("@CHANNEL9") == _channel(9)
    assert cache.get(_channel(9).channel_id) == _channel(9)


def test_channel_cache_expires(monkeypatch):
    monkeypatch.setattr(current_config, "channel_cache_ttl", timedelta(hours=1))
    cache = ChannelCache()
    cache.put("@channel1", _channel(1))
    assert cache.get("@channel1") == _channel(1)
    monkeypatch.setattr("yourss.youtube.cache.monotonic", lambda: 10**9)
    assert cache.get("@channel1") is None
    assert len(cache) == 1  # the other key is dropped when it is read


def test_channel_cache_can_be_disabled(monkeypatch):
    monkeypatch.setattr(current_config, "channel_cache_ttl", timedelta(0))
    cache = ChannelCache()
    cache.put("@channel1", _channel(1))
    assert len(cache) == 0


@pytest.mark.anyio
async def test_channel_page_is_retried_once(monkeypatch):
    from yourss.youtube import YoutubeApi

    good = _page(_channel_data(_tab("videos", selected=True)))
    pages = ["<html>another layout: ytInitialData = JSON.parse('…')</html>", good]
    api = YoutubeApi()

    async def fake_get_page(url: str) -> str:
        return pages.pop(0)

    monkeypatch.setattr(api, "_get_page", fake_get_page)
    page = await api.get_channel_page(CHANNEL_ID, "videos")
    assert page.selected_tab == "videos"
    assert pages == []

    # Two unreadable pages in a row are a real breakage
    pages.extend(["<html>nothing</html>", "<html>nothing</html>"])
    with pytest.raises(ScrapingError):
        await api.get_channel_page(CHANNEL_ID)
