import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND

from ..youtube import PLAYLIST_TABS, ChannelTab, Continuation, YoutubeApi
from ..youtube.utils import CHANNEL_PATTERN
from .jinja import template_page
from .schema import ChannelId, ShownPlaylistId, UserId
from .utils import get_videos_from_feeds, next_page_url


def require_htmx(hx_request: Annotated[str | None, Header()] = None) -> None:
    # A filter, not a security measure: it keeps crawlers and direct visits away from the fragments
    if hx_request != "true":
        raise HTTPException(HTTP_404_NOT_FOUND)


router = APIRouter(prefix="/htmx", dependencies=[Depends(require_htmx)])


@router.get("/channel/{channel}", response_class=HTMLResponse)
async def htmx_channel(
    request: Request, channel: ChannelId | UserId, tab: Annotated[Literal["recent", "playlists"], Query()] = "recent"
) -> HTMLResponse:
    page = await YoutubeApi().get_channel_page(channel)
    return template_page(request, "partials/channel.jinja-html", channel=page.channel, tabs=page.tabs, open_tab=tab)


@router.get("/playlist/{playlist}", response_class=HTMLResponse)
async def htmx_playlist(
    request: Request,
    playlist: ShownPlaylistId,
    tab: Annotated[Literal["recent", "all"], Query()] = "recent",
    channel: Annotated[str | None, Query(pattern=CHANNEL_PATTERN)] = None,
) -> HTMLResponse:
    """The playlist with its Recent tab open, read from the feed fetched for its title, or its All tab; opened from the
    Playlists tab of a `channel`, under the header of that channel (docs/specs/playlist-tabs.md)."""
    api = YoutubeApi()
    if channel is not None:
        owner, feed = await asyncio.gather(api.get_channel(channel), api.get_playlist_rss(playlist))
        return template_page(request, "partials/channel-playlist.jinja-html", channel=owner, playlist=feed)
    feed = await api.get_playlist_rss(playlist)
    # No request for the channels: the ones the cache knows have their avatar, the others their initial
    videos = get_videos_from_feeds([feed], {}) if tab == "recent" else []
    return template_page(request, "partials/playlist.jinja-html", playlist=feed, videos=videos, tab=tab)


@router.get("/playlist/{playlist}/recent", response_class=HTMLResponse)
async def htmx_playlist_recent(request: Request, playlist: ShownPlaylistId) -> HTMLResponse:
    feed = await YoutubeApi().get_playlist_rss(playlist)
    return template_page(request, "partials/videos-container.jinja-html", videos=get_videos_from_feeds([feed], {}))


@router.get("/playlist/{playlist}/all", response_class=HTMLResponse)
async def htmx_playlist_all(request: Request, playlist: ShownPlaylistId) -> HTMLResponse:
    """Every video of the playlist, in its order, scraped from its page a hundred at a time."""
    page = await YoutubeApi().get_playlist_videos(playlist)
    return template_page(
        request,
        "partials/videos-container.jinja-html",
        videos=page.videos,
        next_page_url=next_page_url(page.continuation, playlist=True),
    )


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
    playlist: Annotated[bool, Query()] = False,
    cards: Annotated[bool, Query()] = False,
    owner: Annotated[str | None, Query(pattern=CHANNEL_PATTERN)] = None,
) -> HTMLResponse:
    continuation = Continuation(token=token, client_version=version)
    api = YoutubeApi()
    if cards:
        more = await api.get_more_playlists(continuation)
        return template_page(
            request,
            "partials/playlist-cards.jinja-html",
            playlists=more.playlists,
            owner=owner,
            next_page_url=next_page_url(more.continuation, owner=owner),
        )
    if playlist:
        page = await api.get_more_playlist_videos(continuation)
    else:
        page = await api.get_more_videos(continuation, shorts=shorts)
    return template_page(
        request,
        "partials/videos.jinja-html",
        videos=page.videos,
        next_page_url=next_page_url(page.continuation, shorts=shorts, playlist=playlist),
    )


@router.get("/{tab}/{channel}", response_class=HTMLResponse)
async def htmx_tab(request: Request, tab: ChannelTab, channel: ChannelId | UserId) -> HTMLResponse:
    page = await YoutubeApi().get_channel_page(channel, tab)
    # A channel without this tab gets its home page instead: that is an empty tab, not its videos
    if page.selected_tab != tab:
        return template_page(request, "partials/videos-container.jinja-html", videos=[])
    if tab in PLAYLIST_TABS:
        cards = page.playlists()
        return template_page(
            request,
            "partials/playlist-cards-container.jinja-html",
            playlists=cards.playlists,
            owner=page.channel.channel_id,
            next_page_url=next_page_url(cards.continuation, owner=page.channel.channel_id),
        )
    shorts = tab == "shorts"
    videos = page.videos(shorts=shorts)
    return template_page(
        request,
        "partials/videos-container.jinja-html",
        videos=videos.videos,
        next_page_url=next_page_url(videos.continuation, shorts=shorts),
    )
