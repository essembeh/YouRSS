from typing import Annotated

from fastapi import APIRouter, Query, Request
from starlette.responses import HTMLResponse

from ..youtube import ChannelTab, Continuation, YoutubeApi
from .jinja import template_page
from .schema import ChannelId, UserId
from .utils import next_page_url

router = APIRouter(prefix="/htmx")


@router.get("/channel/{channel}", response_class=HTMLResponse)
async def htmx_channel(request: Request, channel: ChannelId | UserId) -> HTMLResponse:
    page = await YoutubeApi().get_channel_page(channel)
    return template_page(request, "partials/channel.jinja-html", channel=page.channel, tabs=page.tabs)


@router.get("/rss/{channel}", response_class=HTMLResponse)
async def htmx_rss(request: Request, channel: ChannelId | UserId) -> HTMLResponse:
    feed = await YoutubeApi().get_channel_rss(channel)
    videos = [entry.to_video() for entry in feed.entries]
    return template_page(request, "partials/videos-container.jinja-html", videos=videos)


@router.get("/next", response_class=HTMLResponse)
async def htmx_next(
    request: Request,
    token: Annotated[str, Query()],
    version: Annotated[str, Query()],
    shorts: Annotated[bool, Query()] = False,
) -> HTMLResponse:
    continuation = Continuation(token=token, client_version=version)
    page = await YoutubeApi().get_more_videos(continuation, shorts=shorts)
    return template_page(
        request,
        "partials/videos.jinja-html",
        videos=page.videos,
        next_page_url=next_page_url(page.continuation, shorts=shorts),
    )


@router.get("/{tab}/{channel}", response_class=HTMLResponse)
async def htmx_tab(request: Request, tab: ChannelTab, channel: ChannelId | UserId) -> HTMLResponse:
    page = await YoutubeApi().get_channel_page(channel, tab)
    # A channel without this tab gets its home page instead: that is an empty tab, not its videos
    if page.selected_tab != tab:
        return template_page(request, "partials/videos-container.jinja-html", videos=[])
    shorts = tab == "shorts"
    videos = page.videos(shorts=shorts)
    return template_page(
        request,
        "partials/videos-container.jinja-html",
        videos=videos.videos,
        next_page_url=next_page_url(videos.continuation, shorts=shorts),
    )
