import asyncio
from datetime import timedelta
from pathlib import Path

from loguru import logger
from pytest import MonkeyPatch

from yourss.async_utils import async_fetch
from yourss.main import lifespan
from yourss.security import read_config
from yourss.settings import current_config
from yourss.warmup import warm_forever, warm_interval, warm_round
from yourss.youtube import YoutubeApi


async def test_warm_round_refreshes_every_page() -> None:
    lines: list[str] = []
    handler = logger.add(lambda message: lines.append(message.strip()), level="INFO", format="{message}")
    try:
        await warm_round()
    finally:
        logger.remove(handler)
    (summary,) = [line for line in lines if line.startswith("Warm-up:")]
    # The pages of the sample file but Cards (`warmup: false`), their channels counted once each per page
    assert summary.startswith("Warm-up: 4 pages (1 skipped), 10 channels, 0 failed, ")


def _feed_mtimes(folder: Path) -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in folder.glob("*.rss")}


async def test_warm_round_refreshes_whatever_the_age(test_cache_folder: Path) -> None:
    config = read_config()
    assert config is not None
    (skipped,) = [page for page in config.pages if not page.warmup]
    skipped_feeds = {test_cache_folder / f"{channel}.rss" for channel in skipped.channels}
    await async_fetch(skipped.channels, api=YoutubeApi())
    await warm_round()
    before = _feed_mtimes(test_cache_folder)
    await asyncio.sleep(0.01)
    await warm_round()
    # Every feed was fresh (younger than the TTL), every one was written again but those of the skipped page
    after = _feed_mtimes(test_cache_folder)
    assert skipped_feeds and skipped_feeds <= before.keys()
    assert all(after[path] > mtime for path, mtime in before.items() if path not in skipped_feeds)
    assert all(after[path] == before[path] for path in skipped_feeds)


async def test_warm_round_without_a_file(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(current_config, "users_file", None)
    lines: list[str] = []
    handler = logger.add(lambda message: lines.append(message.strip()), level="WARNING", format="{message}")
    try:
        await warm_round()
    finally:
        logger.remove(handler)
    assert lines == ["Warm-up: no pages to refresh"]


async def test_warm_forever_survives_a_failing_round(monkeypatch: MonkeyPatch) -> None:
    rounds = 0

    async def failing_round() -> None:
        nonlocal rounds
        rounds += 1
        raise RuntimeError("boom")

    monkeypatch.setattr("yourss.warmup.warm_round", failing_round)
    lines: list[str] = []
    handler = logger.add(lambda message: lines.append(message.strip()), level="ERROR", format="{message}")
    task = asyncio.create_task(warm_forever(timedelta(milliseconds=10)))
    try:
        await asyncio.sleep(0.05)
    finally:
        task.cancel()
        logger.remove(handler)
    assert rounds >= 2 and all(line.startswith("Warm-up round failed: boom") for line in lines) and lines


def test_warm_interval_is_a_minute_before_the_ttl() -> None:
    assert warm_interval(timedelta(minutes=30)) == timedelta(minutes=29)
    assert warm_interval(timedelta(hours=1)) == timedelta(minutes=59)
    # A very short TTL still gets a positive interval, shorter than itself
    assert warm_interval(timedelta(minutes=1)) == timedelta(seconds=30)


async def test_lifespan_starts_the_warm_up_when_enabled(monkeypatch: MonkeyPatch) -> None:
    started: list[timedelta] = []

    async def fake_forever(interval: timedelta) -> None:
        started.append(interval)
        await asyncio.sleep(3600)

    monkeypatch.setattr("yourss.main.warm_forever", fake_forever)
    monkeypatch.setattr(current_config, "cache_rss_ttl", timedelta(minutes=30))
    monkeypatch.setattr(current_config, "warmup_enabled", False)
    async with lifespan(None):  # type: ignore[arg-type]
        pass
    assert started == []
    monkeypatch.setattr(current_config, "warmup_enabled", True)
    async with lifespan(None):  # type: ignore[arg-type]
        await asyncio.sleep(0)
    assert started == [timedelta(minutes=29)]
    # Without a cache there is nothing to warm up
    monkeypatch.setattr(current_config, "cache_enabled", False)
    async with lifespan(None):  # type: ignore[arg-type]
        await asyncio.sleep(0)
    assert started == [timedelta(minutes=29)]
