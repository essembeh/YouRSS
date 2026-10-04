from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND

from ..youtube import ChannelTab, Continuation, YoutubeApi
from ..youtube.cache import channel_cache
from .jinja import template_page
from .schema import ChannelId, PlaylistId, UserId
from .utils import get_videos_from_feeds, next_page_url


def require_htmx(hx_request: Annotated[str | None, Header()] = None) -> None:
    # A filter, not a security measure: it keeps crawlers and direct visits away from the fragments
    if hx_request != "true":
        raise HTTPException(HTTP_404_NOT_FOUND)


router = APIRouter(prefix="/htmx", dependencies=[Depends(require_htmx)])


@router.get("/channel/{channel}", response_class=HTMLResponse)
async def htmx_channel(request: Request, channel: ChannelId | UserId) -> HTMLResponse:
    page = await YoutubeApi().get_channel_page(channel)
    return template_page(request, "partials/channel.jinja-html", channel=page.channel, tabs=page.tabs)


@router.get("/playlist/{playlist}", response_class=HTMLResponse)
async def htmx_playlist(request: Request, playlist: PlaylistId) -> HTMLResponse:
    feed = await YoutubeApi().get_playlist_rss(playlist)
    # No request for the channels: the ones the cache knows have their avatar, the others their initial
    channels = {entry.channel_id: channel_cache.get(entry.channel_id) for entry in feed.entries}
    videos = get_videos_from_feeds([feed], {key: channel for key, channel in channels.items() if channel is not None})
    return template_page(request, "partials/playlist.jinja-html", playlist=feed, videos=videos)


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
