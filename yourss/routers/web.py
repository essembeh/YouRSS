from datetime import datetime

import arrow
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from httpx import AsyncClient
from jinja2 import Environment, FileSystemLoader
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND

import yourss

from ..async_utils import afetch_feeds
from ..schema import Theme, User
from ..security import get_auth_user
from ..settings import current_config, templates_folder
from ..youtube import Feed, YoutubeRssApi, YoutubeWebApi
from .utils import custom_template_response, get_youtube_web_client, parse_channel_names


def clean_title(text: str) -> str:
    if current_config.clean_titles:
        return text.capitalize()
    return text


def date_humanize(date: datetime) -> str:
    return arrow.get(date).humanize()


# Jinja customization
env = Environment(loader=FileSystemLoader(templates_folder))
env.filters["clean_title"] = clean_title
env.filters["date_humanize"] = date_humanize
ViewTemplateResponse = custom_template_response(
    Jinja2Templates(env=env),
    "view.html",
    version=yourss.__version__,
    open_primary=current_config.open_primary,
    open_secondary=current_config.open_secondary,
)

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("view_channels", channels=current_config.default_channels)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(
        f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1&control=2&rel=0"
    )


@router.get("/u/{username}", response_class=HTMLResponse)
async def get_user(
    request: Request,
    yt_client: AsyncClient = Depends(get_youtube_web_client),
    theme: Theme | None = None,
    user: User = Depends(get_auth_user),
):
    feeds = await afetch_feeds(
        user.channels, rss_api=YoutubeRssApi(), web_api=YoutubeWebApi(yt_client)
    )
    active_feeds = [f for f in feeds.values() if isinstance(f, Feed)]
    if len(active_feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    return ViewTemplateResponse(
        request=request,
        title=f"/u/{user.name}",
        feeds=active_feeds,
        theme=theme or user.theme or current_config.theme,
    )


@router.get("/{channels}", response_class=HTMLResponse)
async def view_channels(
    request: Request,
    channels: str,
    yt_client: AsyncClient = Depends(get_youtube_web_client),
    theme: Theme | None = None,
):
    feeds = await afetch_feeds(
        parse_channel_names(channels),
        rss_api=YoutubeRssApi(),
        web_api=YoutubeWebApi(yt_client),
    )
    active_feeds = [f for f in feeds.values() if isinstance(f, Feed)]
    if len(active_feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    return ViewTemplateResponse(
        request=request,
        title=", ".join(sorted(map(lambda f: f.title, active_feeds))),
        feeds=active_feeds,
        theme=theme or current_config.theme,
    )
