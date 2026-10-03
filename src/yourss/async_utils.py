import asyncio

from .youtube import ChannelDescription, Feed, YoutubeApi, is_playlist_id


async def async_fetch(
    names: list[str], api: YoutubeApi
) -> tuple[dict[str, ChannelDescription], list[Feed], list[BaseException]]:
    channels: dict[str, ChannelDescription] = {}
    feeds: list[Feed] = []
    errors: list[BaseException] = []

    # first fetch user/channel_id metadata
    for channel in await asyncio.gather(
        *[api.get_channel(n) for n in names if not is_playlist_id(n)],
        return_exceptions=True,
    ):
        if isinstance(channel, BaseException):
            errors.append(channel)
        else:
            channels[channel.channel_id] = channel

    # then fetch feeds
    for feed in await asyncio.gather(*[api.get_channel_rss(n) for n in channels], return_exceptions=True):
        if isinstance(feed, BaseException):
            errors.append(feed)
        else:
            feeds.append(feed)

    # fetch playlists
    playlist_channels_id: list[str] = []
    for feed in await asyncio.gather(
        *[api.get_playlist_rss(n) for n in names if is_playlist_id(n)],
        return_exceptions=True,
    ):
        if isinstance(feed, BaseException):
            errors.append(feed)
        else:
            feeds.append(feed)
            if feed.channel_id and feed.channel_id not in channels:
                playlist_channels_id.append(feed.channel_id)

    # fetch metadata for missing playlist channels
    for channel in await asyncio.gather(*[api.get_channel(n) for n in playlist_channels_id], return_exceptions=True):
        if isinstance(channel, BaseException):
            errors.append(channel)
        else:
            channels[channel.channel_id] = channel

    return channels, feeds, errors
