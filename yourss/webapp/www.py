from enum import Enum
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from loguru import logger
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND

import yourss

from ..config import current_config
from ..users import User, get_auth_user
from ..utils import custom_template_response, parse_channel_names
from ..youtube import YoutubeWebClient
from .utils import get_youtube_client


def clean_title(text: str) -> str:
    if current_config.CLEAN_TITLES:
        return text.capitalize()
    return text


class Theme(str, Enum):
    light = "light"
    dark = "dark"


# Jinja customization
env = Environment(loader=FileSystemLoader(Path(yourss.__file__).parent / "templates"))
env.filters["clean_title"] = clean_title
ViewTemplateResponse = custom_template_response(
    Jinja2Templates(env=env),
    "view.html",
    version=yourss.__version__,
    open_primary=current_config.OPEN_PRIMARY,
    open_secondary=current_config.OPEN_SECONDARY,
)

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("view_channels", channels=current_config.DEFAULT_CHANNELS)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(
        f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1&control=2&rel=0"
    )


@router.get("/u/{username}", response_class=HTMLResponse)
async def get_user(
    request: Request,
    yt_client: Annotated[YoutubeWebClient, Depends(get_youtube_client)],
    theme: Theme | None = None,
    user: User = Depends(get_auth_user),
):
    feeds = []
    for name in user.channels:
        try:
            feeds.append(await yt_client.get_rss_feed(name))
        except BaseException as error:
            logger.exception("Cannot get rss feed for {}: {}", name, error)

    if len(feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    return ViewTemplateResponse(
        request=request,
        title=f"/u/{user.name}",
        feeds=feeds,
        theme=theme.value if theme is not None else current_config.THEME,
    )


@router.get("/{channels}", response_class=HTMLResponse)
async def view_channels(
    request: Request,
    channels: str,
    yt_client: Annotated[YoutubeWebClient, Depends(get_youtube_client)],
    theme: Theme | None = None,
):
    feeds = []
    for name in parse_channel_names(channels):
        try:
            feeds.append(await yt_client.get_rss_feed(name))
        except BaseException as error:
            logger.exception("Cannot get rss feed for {}: {}", name, error)

    if len(feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    return ViewTemplateResponse(
        request=request,
        title=", ".join(sorted(map(lambda f: f.title, feeds))),
        feeds=feeds,
        theme=theme.value if theme is not None else current_config.THEME,
    )
