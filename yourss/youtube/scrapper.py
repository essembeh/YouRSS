import json
import re
from asyncio import sleep
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, List, Self

from bs4 import BeautifulSoup
from httpx import Response

from .client import YoutubeApi
from .model import (
    BrowseData,
    VideoDescription,
    YoutubeMetadata,
)
from .utils import json_first

YTCFG_PATTERN = r"ytcfg\.set\((?P<json>(?:\"[^\"]*\"|'[^']*'|[^()])*)\)"
YTINITIALDATA_PATTERN = r"ytInitialData = (?P<json>{.*?});"


@dataclass
class PageScrapper:
    soup: BeautifulSoup

    @classmethod
    def from_response(cls, resp: Response) -> Self:
        resp.raise_for_status()
        return cls(soup=BeautifulSoup(resp.text, features="html.parser"))

    def get_metadata(self) -> YoutubeMetadata:
        return YoutubeMetadata(
            {
                m["property"]: m.get("content")
                for m in self.soup.find_all("meta")
                if "property" in m.attrs
            }
        )

    def iter_scripts(self) -> Iterator[str]:
        for script in self.soup.find_all("script"):
            if script.string is not None:
                yield script.string

    def find_browse_data(self) -> BrowseData | None:
        for script in self.iter_scripts():
            if (m := re.search(YTINITIALDATA_PATTERN, script, re.DOTALL)) is not None:
                return BrowseData.from_json_string(m.group("json"))

    def find_client_data(self) -> Dict[str, Any] | None:
        for script in self.iter_scripts():
            if (
                "INNERTUBE_CONTEXT" in script
                and (m := re.search(YTCFG_PATTERN, script, re.DOTALL)) is not None
            ):
                payload = json.loads(m.group("json"))
                return json_first("$.INNERTUBE_CONTEXT.client", payload)


@dataclass
class VideoScrapper:
    youtube_api: YoutubeApi = field(default_factory=YoutubeApi)

    async def iter_videos(
        self, channel: str, *, delay: float = 0
    ) -> AsyncIterator[List[VideoDescription]]:
        homepage = PageScrapper.from_response(
            await self.youtube_api.get_homepage(channel, suffix="/videos")
        )
        assert (client_data := homepage.find_client_data()) is not None
        assert (browse_data := homepage.find_browse_data()) is not None
        while True:
            videos = list(browse_data.iter_videos())
            if len(videos) > 0:
                # yield all videos from the page
                yield videos
            else:
                # could not find any video
                break
            if browse_data.continuation_token is None:
                # no continuation token, stop
                break
            # get next page using json api
            if delay > 0:
                await sleep(delay)
            browse_data = await self.get_next_page(
                client_data,
                browse_data.click_tracking_params,
                browse_data.continuation_token,
            )

    async def get_next_page(
        self,
        client_data: Dict[str, Any],
        click_tracking_params: str,
        continuation_token: str,
    ) -> BrowseData:
        resp = await self.youtube_api.api_browse(
            {
                "context": {
                    "clickTracking": {"clickTrackingParams": click_tracking_params},
                    "client": client_data,
                },
                "continuation": continuation_token,
            }
        )
        return BrowseData(resp)
