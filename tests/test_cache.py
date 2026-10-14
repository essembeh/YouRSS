import os
from datetime import timedelta
from pathlib import Path

from httpx import ConnectTimeout, HTTPStatusError, Request, Response
from pydantic import ValidationError
from pytest import MonkeyPatch, fixture, mark, raises

from yourss.schema import AppSettings
from yourss.settings import current_config, setup_cache_folder
from yourss.youtube.cache import read_cached_feed
from yourss.youtube.client import YoutubeApi
from yourss.youtube.schema import Feed

SAMPLES_FOLDER = Path(__file__).parent / "data"
CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"
# Older than any ttl used in the tests
OLD_MTIME = 1_000_000

# The mocked api, its call counter and the cache folder
type ApiFixture = tuple[YoutubeApi, dict[str, int], Path]


def _http_error(status: int) -> HTTPStatusError:
    request = Request("GET", "https://www.youtube.com/feeds/videos.xml")
    return HTTPStatusError(str(status), request=request, response=Response(status, request=request))


FETCH_ERRORS = [_http_error(404), _http_error(500), ConnectTimeout("timeout")]


@fixture
def sample_bytes() -> bytes:
    return (SAMPLES_FOLDER / f"{CHANNEL_ID}.xml").read_bytes()


@fixture
def api(monkeypatch: MonkeyPatch, tmp_path: Path, sample_bytes: bytes) -> ApiFixture:
    """A YoutubeApi whose raw fetch is mocked, with a call counter, and the cache enabled."""
    monkeypatch.setattr(current_config, "cache_enabled", True)
    monkeypatch.setattr(current_config, "cache_folder", tmp_path)
    monkeypatch.setattr(current_config, "cache_ttl", timedelta(minutes=10))
    monkeypatch.setattr(current_config, "cache_fallback_ttl", timedelta(hours=24))

    calls = {"count": 0}

    async def fake_raw(channel_id: str) -> Feed:
        calls["count"] += 1
        feed = Feed.from_xml(sample_bytes)
        # simulate rapid_api_client populating _response with a fake carrier
        feed._response = type("R", (), {"content": sample_bytes})()
        return feed

    instance = YoutubeApi()
    monkeypatch.setattr(instance, "_get_channel_rss_raw", fake_raw)
    return instance, calls, tmp_path


def _fail_with(monkeypatch: MonkeyPatch, instance: YoutubeApi, calls: dict[str, int], error: Exception) -> None:
    async def fetch_error(channel_id: str) -> Feed:
        calls["count"] += 1
        raise error

    monkeypatch.setattr(instance, "_get_channel_rss_raw", fetch_error)


async def test_fresh_cache_skips_the_fetch(api: ApiFixture) -> None:
    instance, calls, tmp_path = api

    first = await instance.get_channel_rss(CHANNEL_ID)
    second = await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 1
    assert first.uid == second.uid == CHANNEL_ID
    assert (tmp_path / f"{CHANNEL_ID}.rss").is_file()


async def test_expired_cache_is_fetched_again(api: ApiFixture) -> None:
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

    assert calls["count"] == 2
    assert not any(tmp_path.iterdir())


@mark.parametrize("error", FETCH_ERRORS, ids=type)
async def test_fetch_error_serves_the_cache(monkeypatch: MonkeyPatch, api: ApiFixture, error: Exception) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    # too old to be served directly, young enough for the fallback
    monkeypatch.setattr(current_config, "cache_ttl", timedelta(0))
    _fail_with(monkeypatch, instance, calls, error)

    feed = await instance.get_channel_rss(CHANNEL_ID)

    assert calls["count"] == 2  # fetch attempted and failed
    assert feed.uid == CHANNEL_ID  # served from the cache
    assert path.is_file()  # kept


async def test_fetch_error_drops_the_dead_cache_and_raises(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, tmp_path = api
    path = tmp_path / f"{CHANNEL_ID}.rss"

    await instance.get_channel_rss(CHANNEL_ID)
    os.utime(path, (OLD_MTIME, OLD_MTIME))
    _fail_with(monkeypatch, instance, calls, _http_error(404))

    with raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)

    assert not path.is_file()


async def test_fetch_error_without_cache_raises(monkeypatch: MonkeyPatch, api: ApiFixture) -> None:
    instance, calls, _tmp_path = api
    _fail_with(monkeypatch, instance, calls, _http_error(404))

    with raises(HTTPStatusError):
        await instance.get_channel_rss(CHANNEL_ID)


def test_read_cached_feed_missing(tmp_path: Path) -> None:
    assert read_cached_feed(tmp_path, "does-not-exist", timedelta(hours=1)) is None


def test_read_cached_feed_corrupted(tmp_path: Path) -> None:
    (tmp_path / "broken.rss").write_bytes(b"not xml")
    assert read_cached_feed(tmp_path, "broken", timedelta(hours=1)) is None


def test_settings_ttl_must_not_exceed_fallback_ttl() -> None:
    with raises(ValidationError):
        AppSettings(cache_ttl=timedelta(hours=2), cache_fallback_ttl=timedelta(hours=1))


def test_setup_cache_folder_creates_the_given_folder(tmp_path: Path) -> None:
    config = AppSettings(cache_enabled=True, cache_folder=tmp_path / "rss")
    setup_cache_folder(config)
    assert (tmp_path / "rss").is_dir()


def test_setup_cache_folder_picks_a_temporary_folder() -> None:
    config = AppSettings(cache_enabled=True, cache_folder=None)
    setup_cache_folder(config)
    assert config.cache_folder is not None
    assert config.cache_folder.is_dir()
    assert config.cache_folder.name.startswith("yourss-")
    config.cache_folder.rmdir()


def test_setup_cache_folder_disabled_leaves_the_folder_alone(tmp_path: Path) -> None:
    config = AppSettings(cache_enabled=False, cache_folder=tmp_path / "rss")
    setup_cache_folder(config)
    assert not (tmp_path / "rss").exists()
