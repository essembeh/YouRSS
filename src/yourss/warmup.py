"""
Background refresh of the feeds of every page of the users file (docs/specs/pages-users.md §8).
"""

import asyncio
from datetime import timedelta
from time import monotonic

from loguru import logger

from .async_utils import State, async_fetch
from .security import read_config
from .youtube import YoutubeApi


async def warm_round() -> None:
    """Fetch every page in the order of the file: a channel in several pages is asked once, the cache answers next."""
    config = read_config()
    if config is None:
        logger.warning("Warm-up: no pages to refresh")
        return
    start = monotonic()
    api = YoutubeApi()
    channels = failed = 0
    for page in config.pages:
        statuses = await async_fetch(page.channels, api=api)
        channels += len(statuses)
        failed += sum(status.state == State.FAILED for status in statuses)
    logger.info(
        "Warm-up: {} pages, {} channels, {} failed, {:.1f}s", len(config.pages), channels, failed, monotonic() - start
    )


async def warm_forever(interval: timedelta) -> None:
    """A round now, then one per interval; a round that fails is logged and the next one still comes."""
    while True:
        try:
            await warm_round()
        except Exception as error:
            logger.exception("Warm-up round failed: {}", error)
        await asyncio.sleep(interval.total_seconds())
