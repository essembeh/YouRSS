import asyncio
from typing import Dict, List

from .youtube import (
    Feed,
    YoutubeApi,
    is_channel_id,
    is_playlist_id,
    is_user,
)
from .youtube.scrapper import PageScrapper


async def _fetch_feed(name: str, *, api: YoutubeApi) -> Feed:
    if is_playlist_id(name):
        return await api.get_playlist_rss(name)

    # if given id is a name, get the channel id
    if is_user(name):
        page = PageScrapper.from_response(await api.get_homepage(name))
        meta = page.get_metadata()
        name = meta.channel_id

    # check valid channel id
    if not is_channel_id(name):
        raise ValueError(f"Invalid channel id: {name}")

    return await api.get_channel_rss(name)


async def afetch_feeds(
    names: List[str], *, api: YoutubeApi
) -> Dict[str, Feed | BaseException]:
    return {
        name: task
        for name, task in zip(
            names,
            await asyncio.gather(
                *[_fetch_feed(name, api=api) for name in names],
                return_exceptions=True,
            ),
        )
    }
