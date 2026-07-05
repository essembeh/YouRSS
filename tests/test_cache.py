import os
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import HTTPStatusError, Request, Response

from yourss.settings import current_config
from yourss.youtube.cache import read_stale_feed
from yourss.youtube.client import YoutubeApi
from yourss.youtube.schema import Feed

SAMPLES_FOLDER = Path(__file__).parent.parent / "samples"
CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"


def _http_404() -> HTTPStatusError:
    request = Request("GET", "https://www.youtube.com/feeds/videos.xml")
    return HTTPStatusError(
        "404", request=request, response=Response(404, request=request)
    )


@pytest.fixture
def sample_bytes() -> bytes:
    return (SAMPLES_FOLDER / f"{CHANNEL_ID}.xml").read_bytes()


@pytest.fixture
def api(monkeypatch, tmp_path, sample_bytes):
    """A YoutubeApi whose raw fetch is mocked, with a call counter.

    The on-disk file is only a 404 fallback, not a cache: the feed is always
    fetched live.
    """
    monkeypatch.setattr(current_config, "cache_folder", tmp_path)
    monkeypatch.setattr(current_config, "cache_max_age", timedelta(hours=24))

    calls = {"count": 0}

    async def fake_raw(channel_id: str) -> Feed:
        calls["count"] += 1
        feed = Feed.from_xml(sample_bytes)
        # simulate rapid_api_client populating _response with a fake carrier
        feed._response = type("R", (), {"content": sample_bytes})()  # type: ignore[assignment]
        return feed

    instance = YoutubeApi()
    monkeypatch.setattr(instance, "_get_channel_rss_raw", fake_raw)
    return instance, calls, tmp_path


@pytest.mark.anyio
async def test_always_fetches_and_stores_fallback(api):
    instance, calls, tmp_path = api

    first = await instance.get_channel_rss(CHANNEL_ID)
    second = await instance.get_channel_rss(CHANNEL_ID)

    # always fetched live, even with a file already present
    assert calls["count"] == 2
    assert first.uid == second.uid == CHANNEL_ID
    assert (tmp_path / f"{CHANNEL_ID}.rss").is_file()


@pytest.mark.anyio
async def test_disabled_fetches_without_file(monkeypatch, api):
    instance, calls, tmp_path = api
    monkeypatch.setattr(current_config, "cache_folder", None)

    await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 1
    assert not any(tmp_path.iterdir())


@pytest.mark.anyio
async def test_404_serves_stale_fallback(monkeypatch, api):
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    # first successful fetch stores the fallback file
    await instance.get_channel_rss(CHANNEL_ID)

    async def fetch_404(channel_id: str) -> Feed:
        calls["count"] += 1
        raise _http_404()

    monkeypatch.setattr(instance, "_get_channel_rss_raw", fetch_404)

    feed = await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 2  # fetch attempted and failed
    assert feed.uid == CHANNEL_ID  # served from fallback
    assert path.is_file()  # kept


@pytest.mark.anyio
async def test_404_drops_dead_fallback_and_raises(monkeypatch, api):
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    monkeypatch.setattr(current_config, "cache_max_age", timedelta(seconds=1))
    old = 1_000_000  # far older than max_age
    os.utime(path, (old, old))

    async def fetch_404(channel_id: str) -> Feed:
        raise _http_404()

    monkeypatch.setattr(instance, "_get_channel_rss_raw", fetch_404)

    with pytest.raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)

    assert not path.is_file()  # dead fallback dropped


@pytest.mark.anyio
async def test_404_without_fallback_raises(monkeypatch, api):
    instance, calls, tmp_path = api

    async def fetch_404(channel_id: str) -> Feed:
        raise _http_404()

    monkeypatch.setattr(instance, "_get_channel_rss_raw", fetch_404)

    with pytest.raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)


@pytest.mark.anyio
async def test_non_404_error_propagates(monkeypatch, api):
    instance, calls, tmp_path = api

    # a fallback file exists but non-404 errors must not use it
    await instance.get_channel_rss(CHANNEL_ID)

    async def fetch_500(channel_id: str) -> Feed:
        request = Request("GET", "https://x")
        raise HTTPStatusError(
            "500", request=request, response=Response(500, request=request)
        )

    monkeypatch.setattr(instance, "_get_channel_rss_raw", fetch_500)

    with pytest.raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)


def test_read_stale_feed_missing(tmp_path):
    assert read_stale_feed(tmp_path, "does-not-exist", timedelta(hours=1)) is None
