from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND

from ..async_utils import async_fetch
from ..schema import User
from ..security import get_auth_user
from ..settings import current_config
from ..youtube import YoutubeApi
from .jinja import template_page
from .proxy import router as proxy_router
from .schema import ChannelId, UserId
from .utils import get_videos_from_feeds, parse_channel_names

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("page", names=current_config.default_channels)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(proxy_router.url_path_for("player", video_id=video))


@router.get("/user/{username}", response_class=HTMLResponse)
@router.get("/u/{username}", response_class=HTMLResponse)
async def user(request: Request, user: User = Depends(get_auth_user)):
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
        theme=user.theme,
        lang=user.lang,
    )


@router.get("/{names}", response_class=HTMLResponse)
async def page(request: Request, names: str):
    api = YoutubeApi()
    channels, feeds, errors = await async_fetch(parse_channel_names(names), api=api)
    videos = get_videos_from_feeds(feeds, channels)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=", ".join(
            sorted(map(lambda x: x.name, channels.values()), key=str.lower)
        ),
        channels=sorted(channels.values(), key=lambda c: c.name.lower()),
        videos=videos,
        errors=errors,
    )


@router.get("/channel/{channel}", response_class=HTMLResponse)
@router.get("/c/{channel}", response_class=HTMLResponse)
async def channel(request: Request, channel: ChannelId | UserId):
    api = YoutubeApi()
    try:
        homepage = await api.get_homepage(channel)
        channel_desc = homepage.get_metadata()
    except Exception as e:
        raise HTTPException(HTTP_404_NOT_FOUND, detail=str(e))

    return template_page(
        request,
        "pages/channel.jinja-html",
        title=f"/c/{channel}",
        channel=channel_desc,
    )
