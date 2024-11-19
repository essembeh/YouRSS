from typing import Any, Dict, List
from urllib.parse import urlencode

from ..youtube import BrowseData, ChannelDescription, Feed, VideoDescription


def force_https(url: str) -> str:
    assert isinstance(url, str)
    if url.startswith("http:"):
        return url.replace("http:", "https:", 1)
    return url


def parse_channel_names(text: str, delimiter: str = ",") -> List[str]:
    return list(
        set(filter(lambda s: len(s) > 0, map(str.strip, text.split(delimiter))))
    )


def build_url(base_url: str, params: Dict[str, Any]) -> str:
    return base_url + "?" + urlencode(params)


def next_page_url(browse_data: BrowseData, url: str, shorts: bool) -> str | None:
    if browse_data.continuation_token is not None:
        return build_url(
            url,
            {
                "click_tracking_params": browse_data.click_tracking_params,
                "continuation_token": browse_data.continuation_token,
                "shorts": shorts,
            },
        )


def get_videos_from_feeds(
    feeds: List[Feed], channels: Dict[str, ChannelDescription]
) -> List[VideoDescription]:
    out = []
    for feed in feeds:
        for entry in feed.entries:
            channel = channels.get(entry.channel_id)
            if channel is None:
                channel = ChannelDescription(
                    channel_id=entry.channel_id,
                    name=entry.author.name,
                    home=str(entry.author.uri),
                    avatar=None,
                )
            out.append(
                VideoDescription(
                    video_id=entry.video_id,
                    title=entry.title,
                    published=entry.published,
                    thumbnail=str(entry.media_info.thumbnail.url),
                    channel=channel,
                )
            )
    return sorted(out, key=lambda v: v.published, reverse=True)
