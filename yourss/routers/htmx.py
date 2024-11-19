import json
from typing import Annotated

from fastapi import APIRouter, Cookie, Query, Request
from starlette.responses import HTMLResponse

from ..schema import Theme
from ..youtube import VideoDescription, YoutubeApi
from .jinja import (
    template_page,
)
from .schema import ChannelId, UserId
from .utils import next_page_url

router = APIRouter()


@router.get("/channel/{channel}", response_class=HTMLResponse)
async def htmx_channel(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = await api.get_homepage(channel)
    desc = homepage.get_metadata()
    return template_page(request, "partials/channel.jinja-html", channel=desc)


@router.get("/rss/{channel}", response_class=HTMLResponse)
async def htmx_rss(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    feed = await api.get_channel_rss(channel)
    videos = [
        VideoDescription(
            video_id=e.video_id,
            title=e.title,
            published=e.published,
            thumbnail=str(e.media_info.thumbnail.url),
        )
        for e in feed.entries
    ]
    return template_page(request, "partials/videos-container.jinja-html", videos=videos)


@router.get("/videos/{channel}", response_class=HTMLResponse)
async def htmx_videos(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = await api.get_homepage(channel, suffix="/videos")
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None
    out = template_page(
        request,
        "partials/videos-container.jinja-html",
        videos=list(browse_data.iter_videos()),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=False),
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/streams/{channel}", response_class=HTMLResponse)
async def htmx_streams(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = await api.get_homepage(channel, suffix="/streams")
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None
    out = template_page(
        request,
        "partials/videos-container.jinja-html",
        videos=list(browse_data.iter_videos()),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=False),
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/shorts/{channel}", response_class=HTMLResponse)
async def htmx_shorts(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = await api.get_homepage(channel, suffix="/shorts")
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None
    out = template_page(
        request,
        "partials/videos-container.jinja-html",
        videos=list(browse_data.iter_videos(shorts=True)),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=True),
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/next", response_class=HTMLResponse)
async def htmx_next(
    request: Request,
    client_data: Annotated[str, Cookie()],
    click_tracking_params: Annotated[str, Query()],
    continuation_token: Annotated[str, Query()],
    shorts: Annotated[bool, Query()] = False,
):
    api = YoutubeApi()
    browse_data = await api.get_next_page(
        json.loads(client_data), click_tracking_params, continuation_token
    )
    return template_page(
        request,
        "partials/videos.jinja-html",
        videos=list(browse_data.iter_videos(shorts=shorts)),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=shorts),
    )
