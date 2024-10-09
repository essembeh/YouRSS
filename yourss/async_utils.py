import asyncio
from typing import Dict, List

from .youtube import (
    Feed,
    YoutubeMetadata,
    YoutubeRssApi,
    YoutubeWebApi,
    is_channel_id,
    is_playlist_id,
    is_user,
)


async def _fetch_feed(
    name: str, *, rss_api: YoutubeRssApi, web_api: YoutubeWebApi
) -> Feed:
    if is_playlist_id(name):
        return await rss_api.get_playlist_rss(name)

    # if given id is a name, get the channel id
    if is_user(name):
        meta = YoutubeMetadata.from_response(await web_api.get_homepage(name))
        name = meta.channel_id

    # check valid channel id
    if not is_channel_id(name):
        raise ValueError(f"Invalid channel id: {name}")

    return await rss_api.get_channel_rss(name)


async def afetch_feeds(
    names: List[str], *, rss_api: YoutubeRssApi, web_api: YoutubeWebApi
) -> Dict[str, Feed | BaseException]:
    return {
        name: task
        for name, task in zip(
            names,
            await asyncio.gather(
                *[
                    _fetch_feed(name, rss_api=rss_api, web_api=web_api)
                    for name in names
                ],
                return_exceptions=True,
            ),
        )
    }
