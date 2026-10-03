from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from ..async_utils import async_fetch
from ..schema import User
from ..security import get_auth_user
from ..settings import current_config
from ..youtube import YoutubeApi
from .jinja import template_page
from .schema import ChannelId, UserId
from .utils import canonical_names, get_videos_from_feeds, parse_channel_names

router = APIRouter()


def custom_pages_disabled(request: Request) -> HTMLResponse:
    """Error page of the home and of the multi channel pages when the administrator forbids them."""
    return template_page(
        request,
        "pages/error.jinja-html",
        status_code=HTTP_403_FORBIDDEN,
        title="Custom pages are disabled",
        message="The administrator of this instance does not let visitors build their own page.",
    )


@router.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    if not current_config.custom_pages_enabled:
        return custom_pages_disabled(request)
    # The home page is the tutorial: an editable page without any channel yet
    return template_page(request, "pages/home.jinja-html", title="Home", page_names=[])


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)) -> RedirectResponse:
    return RedirectResponse(f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1")


@router.get("/user/{username}", response_class=HTMLResponse)
@router.get("/u/{username}", response_class=HTMLResponse)
async def user(request: Request, user: User = Depends(get_auth_user)) -> HTMLResponse:
    api = YoutubeApi()
    channels, feeds, errors = await async_fetch(user.channels, api=api)
    videos = get_videos_from_feeds(feeds, channels)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=f"/u/{user.name}",
        channels=sorted(channels.values(), key=lambda c: c.name.lower()),
        videos=videos,
        errors=errors,
        # A user page is read-only: it only offers its multi channel copy
        copy_url="/" + ",".join(canonical_names(user.channels)) if current_config.custom_pages_enabled else None,
    )


@router.get("/{names}", response_class=HTMLResponse)
async def page(request: Request, names: str) -> HTMLResponse:
    if not current_config.custom_pages_enabled:
        return custom_pages_disabled(request)
    api = YoutubeApi()
    channel_names = parse_channel_names(names)
    channels, feeds, errors = await async_fetch(channel_names, api=api)
    videos = get_videos_from_feeds(feeds, channels)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=", ".join(sorted((c.name for c in channels.values()), key=str.lower)),
        channels=sorted(channels.values(), key=lambda c: c.name.lower()),
        videos=videos,
        errors=errors,
        # Computed after the fetch, which fills the cache the handles are resolved from
        page_names=canonical_names(channel_names),
    )


@router.get("/channel/{channel}", response_class=HTMLResponse)
@router.get("/c/{channel}", response_class=HTMLResponse)
async def channel(request: Request, channel: ChannelId | UserId) -> HTMLResponse:
    try:
        page = await YoutubeApi().get_channel_page(channel)
    except Exception as e:
        raise HTTPException(HTTP_404_NOT_FOUND, detail=str(e)) from e

    return template_page(
        request,
        "pages/channel.jinja-html",
        title=f"/c/{channel}",
        channel=page.channel,
        tabs=page.tabs,
    )
