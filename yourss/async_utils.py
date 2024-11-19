import asyncio
from typing import Dict, List, Tuple

from .youtube import ChannelDescription, Feed, YoutubeApi, is_playlist_id


async def async_fetch(
    names: List[str], api: YoutubeApi
) -> Tuple[Dict[str, ChannelDescription], List[Feed], List[BaseException]]:
    async def fetch_metadata(name: str) -> ChannelDescription:
        page = await api.get_homepage(name)
        return page.get_metadata()

    channels = {}
    feeds = []
    errors = []

    # first fetch user/channel_id metadata
    for result in await asyncio.gather(
        *[fetch_metadata(n) for n in names if not is_playlist_id(n)],
        return_exceptions=True,
    ):
        if isinstance(result, ChannelDescription):
            channels[result.channel_id] = result
        else:
            errors.append(result)

    # then fetch feeds
    for result in await asyncio.gather(
        *[api.get_channel_rss(n) for n in channels.keys()], return_exceptions=True
    ):
        if isinstance(result, Feed):
            feeds.append(result)
        else:
            errors.append(result)

    # fetch playlists
    playlist_channels_id = []
    for result in await asyncio.gather(
        *[api.get_playlist_rss(n) for n in names if is_playlist_id(n)],
        return_exceptions=True,
    ):
        if isinstance(result, Feed):
            feeds.append(result)
            if result.channel_id and result.channel_id not in channels:
                playlist_channels_id.append(result.channel_id)
        else:
            errors.append(result)

    # fetch metadata for missing playlist channels
    for result in await asyncio.gather(
        *[fetch_metadata(n) for n in playlist_channels_id], return_exceptions=True
    ):
        if isinstance(result, ChannelDescription):
            channels[result.channel_id] = result
        else:
            errors.append(result)

    return channels, feeds, errors
