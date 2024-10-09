from dataclasses import dataclass
from typing import Annotated

from rapid_api_client import Path, RapidApi, get

from .schema import Feed

BASE_URL = "https://www.youtube.com"

CHANNEL_RSS_URL = "/feeds/videos.xml?channel_id={channel_id}"
PLAYLIST_RSS_URL = "/feeds/videos.xml?playlist_id={playlist_id}"


@dataclass
class YoutubeRssApi(RapidApi):
    def __post_init__(self):
        self.client.base_url = BASE_URL

    @get(CHANNEL_RSS_URL, response_class=Feed)
    async def get_channel_rss(self, channel_id: Annotated[str, Path()]): ...

    @get(PLAYLIST_RSS_URL, response_class=Feed)
    async def get_playlist_rss(self, playlist_id: Annotated[str, Path()]): ...
