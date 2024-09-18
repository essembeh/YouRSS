import asyncio
from typing import Iterable

from loguru import logger

from .rss import Feed
from .youtube.client import YoutubeClient


async def get_feeds(client: YoutubeClient, channels: Iterable[str]) -> list[Feed]:
    feeds = await asyncio.gather(
        *[client.get_rss_feed(channel) for channel in channels],
        return_exceptions=True,
    )
    for name, feed in zip(channels, feeds):
        if isinstance(feed, Feed):
            logger.debug("Get feed: {} -> {}", name, feed.get_url())
        else:
            logger.warning("Error with feed: {} -> {}", name, feed)
    return [feed for feed in feeds if isinstance(feed, Feed)]
