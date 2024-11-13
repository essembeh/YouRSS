import json
from datetime import datetime
from typing import Annotated

import arrow
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND

import yourss

from ..async_utils import afetch_feeds
from ..schema import Theme, User
from ..security import get_auth_user
from ..settings import current_config, templates_folder
from ..youtube import Feed, PageScrapper, VideoScrapper, YoutubeApi
from .schema import ChannelId, UserId
from .utils import custom_template_response, parse_channel_names


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
RssTemplateResponse = custom_template_response(
    Jinja2Templates(env=env),
    "rss.html",
    version=yourss.__version__,
    open_primary=current_config.open_primary,
    open_secondary=current_config.open_secondary,
)
ChannelTemplateResponse = custom_template_response(
    Jinja2Templates(env=env), "channel.html", version=yourss.__version__
)
ChannelVideosTemplateResponse = custom_template_response(
    Jinja2Templates(env=env),
    "partials/channel-videos-page.html",
    version=yourss.__version__,
)

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("rss_channels", channels=current_config.default_channels)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(
        f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1&control=2&rel=0"
    )


@router.get("/u/{username}", response_class=HTMLResponse)
async def rss_user(
    request: Request, theme: Theme | None = None, user: User = Depends(get_auth_user)
):
    api = YoutubeApi()
    feeds = await afetch_feeds(user.channels, api=api)
    active_feeds = [f for f in feeds.values() if isinstance(f, Feed)]
    if len(active_feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    return RssTemplateResponse(
        request=request,
        title=f"/u/{user.name}",
        feeds=active_feeds,
        theme=theme or user.theme or current_config.theme,
    )


@router.get("/{channels}", response_class=HTMLResponse)
async def rss_channels(request: Request, channels: str, theme: Theme | None = None):
    api = YoutubeApi()
    feeds = await afetch_feeds(parse_channel_names(channels), api=api)
    active_feeds = [f for f in feeds.values() if isinstance(f, Feed)]
    if len(active_feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    return RssTemplateResponse(
        request=request,
        title=", ".join(sorted(map(lambda f: f.title, active_feeds))),
        feeds=active_feeds,
        theme=theme or current_config.theme,
    )


@router.get("/c/{channel}", response_class=HTMLResponse)
async def videos_channel(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = PageScrapper.from_response(
        await api.get_homepage(channel, suffix="/videos")
    )
    metadata = homepage.get_metadata()
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None

    videos = list(browse_data.iter_videos())
    if len(videos) == 0:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No video found for channel {channel}",
        )

    out = ChannelTemplateResponse(
        request=request,
        metadata=metadata,
        videos=videos,
        theme=theme or current_config.theme,
        click_tracking_params=browse_data.click_tracking_params,
        continuation_token=browse_data.continuation_token,
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/htmx/videos", response_class=HTMLResponse)
async def next(
    request: Request,
    client_data: Annotated[str, Cookie()],
    click_tracking_params: Annotated[str, Query()],
    continuation_token: Annotated[str, Query()],
):
    scrapper = VideoScrapper()
    browse_data = await scrapper.get_next_page(
        json.loads(client_data), click_tracking_params, continuation_token
    )
    videos = list(browse_data.iter_videos())
    out = ChannelVideosTemplateResponse(
        request=request,
        videos=videos,
        click_tracking_params=browse_data.click_tracking_params,
        continuation_token=browse_data.continuation_token,
    )
    return out
