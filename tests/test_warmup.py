import asyncio
from datetime import timedelta
from pathlib import Path

from loguru import logger
from pytest import MonkeyPatch

from yourss.main import lifespan
from yourss.settings import current_config
from yourss.warmup import warm_forever, warm_round


async def test_warm_round_refreshes_every_page() -> None:
    lines: list[str] = []
    handler = logger.add(lambda message: lines.append(message.strip()), level="INFO", format="{message}")
    try:
        await warm_round()
    finally:
        logger.remove(handler)
    (summary,) = [line for line in lines if line.startswith("Warm-up:")]
    # The three pages of the sample file, their channels counted once each per page
    assert summary.startswith("Warm-up: 3 pages, 7 channels, 0 failed, ")


def _feed_mtimes(folder: Path) -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in folder.glob("*.rss")}


async def test_warm_round_refreshes_whatever_the_age(test_cache_folder: Path) -> None:
    await warm_round()
    before = _feed_mtimes(test_cache_folder)
    await asyncio.sleep(0.01)
    await warm_round()
    # Every feed was fresh (younger than the TTL), every one was written again
    after = _feed_mtimes(test_cache_folder)
    assert before and all(after[path] > mtime for path, mtime in before.items())


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


async def test_lifespan_starts_the_warm_up_when_set(monkeypatch: MonkeyPatch) -> None:
    started: list[timedelta] = []

    async def fake_forever(interval: timedelta) -> None:
        started.append(interval)
        await asyncio.sleep(3600)

    monkeypatch.setattr("yourss.main.warm_forever", fake_forever)
    monkeypatch.setattr(current_config, "warmup_interval", None)
    async with lifespan(None):  # type: ignore[arg-type]
        pass
    assert started == []
    monkeypatch.setattr(current_config, "warmup_interval", timedelta(minutes=5))
    async with lifespan(None):  # type: ignore[arg-type]
        await asyncio.sleep(0)
    assert started == [timedelta(minutes=5)]
    # Without a cache there is nothing to warm up
    monkeypatch.setattr(current_config, "cache_enabled", False)
    async with lifespan(None):  # type: ignore[arg-type]
        await asyncio.sleep(0)
    assert started == [timedelta(minutes=5)]
