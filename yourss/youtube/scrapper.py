from asyncio import sleep
from dataclasses import dataclass
from typing import AsyncIterator, List

from .client import YoutubeWebApi
from .metadata import VideoData, VideoDescription, YoutubeWebPage


@dataclass
class VideoScrapper:
    youtube_api: YoutubeWebApi

    async def iter_videos(
        self, channel_id: str, *, shorts: bool = False, delay: float = 0
    ) -> AsyncIterator[List[VideoDescription]]:
        resp = await self.youtube_api.get_html(
            f"https://www.youtube.com/channel/{channel_id}/{'videos' if not shorts else 'shorts'}"
        )
        first_page = YoutubeWebPage(resp)
        assert (client_data := first_page.find_client_data()) is not None
        assert (video_data := first_page.find_initial_video_data()) is not None
        while True:
            videos = list(
                video_data.iter_videos(
                    selector="videoRenderer" if not shorts else "reelItemRenderer"
                )
            )
            if len(videos) > 0:
                # yield all videos from the page
                yield videos
            else:
                # could not find any video
                break
            if video_data.continuation_token is None:
                # no continuation token, stop
                break
            # get next page using json api
            if delay > 0:
                await sleep(delay)
            video_data = VideoData(
                await self.youtube_api.api_browse(
                    {
                        "context": {
                            "clickTracking": {
                                "clickTrackingParams": video_data.click_tracking_params
                            },
                            "client": client_data,
                        },
                        "continuation": video_data.continuation_token,
                    }
                )
            )
