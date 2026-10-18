import json
import os
from datetime import timedelta
from pathlib import Path

from httpx import ConnectTimeout, HTTPStatusError, Request, Response
from pydantic import ValidationError
from pytest import MonkeyPatch, fixture, mark, raises

from yourss.schema import AppSettings
from yourss.settings import current_config, setup_cache_folder
from yourss.youtube import ChannelDescription
from yourss.youtube.cache import known_channel, read_cached_channel, read_cached_feed, write_cached_channel
from yourss.youtube.client import YoutubeApi
from yourss.youtube.schema import Feed

SAMPLES_FOLDER = Path(__file__).parent / "data"
CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"
HANDLE = "@JonnyGiger"
# Older than any ttl used in the tests
OLD_MTIME = 1_000_000

# The mocked api, its call counter and the cache folder
type ApiFixture = tuple[YoutubeApi, dict[str, int], Path]


def _http_error(status: int) -> HTTPStatusError:
    request = Request("GET", "https://www.youtube.com/feeds/videos.xml")
    return HTTPStatusError(str(status), request=request, response=Response(status, request=request))


FETCH_ERRORS = [_http_error(404), _http_error(500), ConnectTimeout("timeout")]


def _channel_page() -> str:
    """The smallest channel page the scraping package reads."""
    data = {
        "metadata": {
            "channelMetadataRenderer": {
                "title": "Jonny Giger",
                "externalId": CHANNEL_ID,
                "channelUrl": f"https://www.youtube.com/channel/{CHANNEL_ID}",
                "vanityChannelUrl": f"http://www.youtube.com/{HANDLE}",
                "avatar": {"thumbnails": [{"url": "https://yt3.googleusercontent.com/abc=s900"}]},
            }
        },
        "contents": {"tabs": []},
    }
    return f"<html><script>var ytInitialData = {json.dumps(data)};</script></html>"


@fixture
def sample_bytes() -> bytes:
    return (SAMPLES_FOLDER / f"{CHANNEL_ID}.xml").read_bytes()


@fixture
def api(monkeypatch: MonkeyPatch, tmp_path: Path, sample_bytes: bytes) -> ApiFixture:
    """A YoutubeApi whose raw RSS fetch and page download are mocked, with a call counter, on an enabled cache."""
    monkeypatch.setattr(current_config, "cache_enabled", True)
    monkeypatch.setattr(current_config, "cache_folder", tmp_path)
    monkeypatch.setattr(current_config, "cache_rss_ttl", timedelta(minutes=30))
    monkeypatch.setattr(current_config, "cache_rss_fallback_ttl", timedelta(hours=48))
    monkeypatch.setattr(current_config, "cache_metadata_ttl", timedelta(hours=24))

    calls = {"count": 0}

    async def fake_raw(channel_id: str) -> Feed:
        calls["count"] += 1
        feed = Feed.from_xml(sample_bytes)
        # simulate rapid_api_client populating _response with a fake carrier
        feed._response = type("R", (), {"content": sample_bytes})()
        return feed

    async def fake_page(url: str) -> str:
        calls["count"] += 1
        return _channel_page()

    instance = YoutubeApi()
    monkeypatch.setattr(instance, "_get_channel_rss_raw", fake_raw)
    monkeypatch.setattr(instance, "_get_page", fake_page)
    return instance, calls, tmp_path


def _fail_with(monkeypatch: MonkeyPatch, instance: YoutubeApi, calls: dict[str, int], error: Exception) -> None:
    async def fetch_error(*args: object) -> Feed:
        calls["count"] += 1
        raise error

    monkeypatch.setattr(instance, "_get_channel_rss_raw", fetch_error)
    monkeypatch.setattr(instance, "_get_page", fetch_error)


# --- Feeds


async def test_fresh_feed_skips_the_fetch(api: ApiFixture) -> None:
    instance, calls, tmp_path = api

    first = await instance.get_channel_rss(CHANNEL_ID)
    second = await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 1
    assert first.uid == second.uid == CHANNEL_ID
    assert (tmp_path / f"{CHANNEL_ID}.rss").is_file()


async def test_refresh_fetches_a_fresh_feed(api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    written = path.stat().st_mtime_ns
    await instance.get_channel_rss(CHANNEL_ID, refresh=True)

    assert calls["count"] == 2
    assert path.stat().st_mtime_ns >= written  # rewritten


@mark.parametrize("error", FETCH_ERRORS, ids=type)
async def test_refresh_error_keeps_the_fresh_feed(monkeypatch: MonkeyPatch, api: ApiFixture, error: Exception) -> None:
    instance, calls, tmp_path = api

    await instance.get_channel_rss(CHANNEL_ID)
    _fail_with(monkeypatch, instance, calls, error)
    feed = await instance.get_channel_rss(CHANNEL_ID, refresh=True)

    assert calls["count"] == 2
    assert feed.uid == CHANNEL_ID and (tmp_path / f"{CHANNEL_ID}.rss").is_file()


async def test_expired_feed_is_fetched_again(api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    os.utime(path, (OLD_MTIME, OLD_MTIME))
    await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 2
    assert path.stat().st_mtime > OLD_MTIME  # refreshed


async def test_disabled_fetches_without_file(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    monkeypatch.setattr(current_config, "cache_enabled", False)

    await instance.get_channel_rss(CHANNEL_ID)
    await instance.get_channel_rss(CHANNEL_ID)
    await instance.get_channel(HANDLE)
    await instance.get_channel(HANDLE)

    assert calls["count"] == 4
    assert not any(tmp_path.iterdir())
    assert known_channel(HANDLE) is None


@mark.parametrize("error", FETCH_ERRORS, ids=type)
async def test_fetch_error_serves_the_feed(monkeypatch: MonkeyPatch, api: ApiFixture, error: Exception) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    # too old to be served directly, young enough for the fallback
    monkeypatch.setattr(current_config, "cache_rss_ttl", timedelta(0))
    _fail_with(monkeypatch, instance, calls, error)

    feed = await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 2  # fetch attempted and failed
    assert feed.uid == CHANNEL_ID  # served from the cache
    assert path.is_file()  # kept


async def test_fetch_error_drops_the_dead_feed_and_raises(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    os.utime(path, (OLD_MTIME, OLD_MTIME))
    _fail_with(monkeypatch, instance, calls, _http_error(404))

    with raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)

    assert not path.is_file()


async def test_fetch_error_without_feed_raises(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, _tmp_path = api
    _fail_with(monkeypatch, instance, calls, _http_error(404))

    with raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)


def test_read_cached_feed_missing(tmp_path: Path) -> None:
    assert read_cached_feed(tmp_path, "does-not-exist", timedelta(hours=1)) is None


def test_read_cached_feed_corrupted(tmp_path: Path) -> None:
    (tmp_path / "broken.rss").write_bytes(b"not xml")
    assert read_cached_feed(tmp_path, "broken", timedelta(hours=1)) is None


# --- Channel metadata


async def test_fresh_channel_skips_the_scrape(api: ApiFixture) -> None:
    instance, calls, tmp_path = api

    first = await instance.get_channel(HANDLE)
    second = await instance.get_channel(HANDLE)
    third = await instance.get_channel(CHANNEL_ID)

    assert calls["count"] == 1
    assert first == second == third
    assert first.channel_id == CHANNEL_ID
    # Known under the lowercased handle and under the channel id
    assert (tmp_path / f"{HANDLE.lower()}.json").is_file()
    assert (tmp_path / f"{CHANNEL_ID}.json").is_file()


async def test_expired_channel_is_scraped_again(api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.json"

    await instance.get_channel(CHANNEL_ID)
    os.utime(path, (OLD_MTIME, OLD_MTIME))
    await instance.get_channel(CHANNEL_ID)

    assert calls["count"] == 2
    assert path.stat().st_mtime > OLD_MTIME


async def test_scrape_error_serves_the_channel_whatever_its_age(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.json"

    expected = await instance.get_channel(CHANNEL_ID)
    os.utime(path, (OLD_MTIME, OLD_MTIME))
    _fail_with(monkeypatch, instance, calls, _http_error(404))

    assert await instance.get_channel(CHANNEL_ID) == expected
    assert calls["count"] == 2
    assert path.is_file()  # never dropped


async def test_scrape_error_without_channel_raises(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, _tmp_path = api
    _fail_with(monkeypatch, instance, calls, _http_error(404))

    with raises(HTTPStatusError):
        await instance.get_channel(CHANNEL_ID)


async def test_channel_page_refreshes_the_channel(api: ApiFixture) -> None:
    instance, _calls, tmp_path = api

    await instance.get_channel_page(CHANNEL_ID, "videos")

    assert read_cached_channel(tmp_path, HANDLE, None) is not None
    assert read_cached_channel(tmp_path, CHANNEL_ID, None) is not None


def test_known_channel_ignores_the_age(api: ApiFixture) -> None:
    _instance, _calls, tmp_path = api
    channel = ChannelDescription(channel_id=CHANNEL_ID, name="Jonny Giger", handle=HANDLE)

    write_cached_channel(tmp_path, "@other", channel)
    for key in ("@other", HANDLE.lower(), CHANNEL_ID):
        os.utime(tmp_path / f"{key}.json", (OLD_MTIME, OLD_MTIME))

    assert known_channel("@OTHER") == channel
    assert known_channel(HANDLE) == channel
    assert known_channel(CHANNEL_ID) == channel
    assert read_cached_channel(tmp_path, CHANNEL_ID, timedelta(hours=1)) is None
    assert known_channel("@unknown") is None


def test_read_cached_channel_corrupted(tmp_path: Path) -> None:
    (tmp_path / "@broken.json").write_bytes(b"{")
    assert read_cached_channel(tmp_path, "@Broken", None) is None


# --- Settings and startup


def test_settings_rss_ttl_must_not_exceed_fallback_ttl() -> None:
    with raises(ValidationError):
        AppSettings(cache_rss_ttl=timedelta(hours=2), cache_rss_fallback_ttl=timedelta(hours=1))


def test_setup_cache_folder_creates_the_given_folder(tmp_path: Path) -> None:
    config = AppSettings(cache_enabled=True, cache_folder=tmp_path / "cache")
    setup_cache_folder(config)
    assert (tmp_path / "cache").is_dir()
    assert not any((tmp_path / "cache").iterdir())  # the probe file is gone


def test_setup_cache_folder_picks_a_temporary_folder() -> None:
    config = AppSettings(cache_enabled=True, cache_folder=None)
    setup_cache_folder(config)
    assert config.cache_folder is not None
    assert config.cache_folder.is_dir()
    assert config.cache_folder.name.startswith("yourss-")
    config.cache_folder.rmdir()


def test_setup_cache_folder_fails_when_not_writable(tmp_path: Path) -> None:
    # A file where the folder should be: neither mkdir nor the probe can work
    (tmp_path / "cache").write_bytes(b"")
    config = AppSettings(cache_enabled=True, cache_folder=tmp_path / "cache")
    with raises(RuntimeError, match="not usable"):
        setup_cache_folder(config)


def test_setup_cache_folder_disabled_leaves_the_folder_alone(tmp_path: Path) -> None:
    config = AppSettings(cache_enabled=False, cache_folder=tmp_path / "cache")
    setup_cache_folder(config)
    assert not (tmp_path / "cache").exists()
