from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

import yourss

from ..cache import get_rssfeeds
from ..config import YOURSS_USERS, config
from ..utils import parse_channel_names

TemplateResponse = Jinja2Templates(
    directory=Path(yourss.__file__).parent / "templates"
).TemplateResponse

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("view_channels", channels=config.DEFAULT_CHANNELS)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(
        f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1&control=2&rel=0"
    )


@router.get("/u/{user}", response_class=HTMLResponse)
async def get_user(request: Request, user: str):
    if user not in YOURSS_USERS:
        raise HTTPException(status_code=404, detail="User not found")

    channel_names = YOURSS_USERS[user]
    assert len(channel_names) > 0
    feeds = await get_rssfeeds(map(lambda x: x.removeprefix("-"), channel_names.keys()))
    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "title": f"/u/{user}",
            "feeds": [f for f in feeds.values() if f is not None],
            "hidden_channel_ids": [
                feed.channel_id
                for name, feed in feeds.items()
                if feed is not None and not channel_names[name]
            ],
        },
    )


@router.get("/{channels}", response_class=HTMLResponse)
async def view_channels(request: Request, channels: str):
    channel_names = parse_channel_names(channels)
    assert len(channel_names) > 0
    feeds = await get_rssfeeds(map(lambda x: x.removeprefix("-"), channel_names.keys()))
    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "title": ", ".join(
                sorted([f.title for f in feeds.values() if f is not None])
            ),
            "feeds": [f for f in feeds.values() if f is not None],
            "hidden_channel_ids": [
                feed.channel_id
                for name, feed in feeds.items()
                if feed is not None and not channel_names[name]
            ],
        },
    )
