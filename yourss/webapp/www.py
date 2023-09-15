from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

import yourss

from ..config import YOURSS_USERS, config
from ..utils import parallel_fetch

TemplateResponse = Jinja2Templates(
    directory=Path(yourss.__file__).parent / "templates"
).TemplateResponse

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("view_channels", channels=config.DEFAULT_CHANNELS)
    )


@router.get("/{channels}", response_class=HTMLResponse)
async def view_channels(request: Request, channels: str):
    feeds = parallel_fetch(set(channels.split(",")))
    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "title": ", ".join(sorted((f.title for f in feeds))),
            "feeds": feeds,
        },
    )


@router.get("/u/{user}", response_class=HTMLResponse)
async def get_user(request: Request, user: str):
    if user not in YOURSS_USERS:
        raise HTTPException(status_code=404, detail="User not found")

    feeds = parallel_fetch(set(YOURSS_USERS[user]))
    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "title": f"/u/{user}",
            "feeds": feeds,
        },
    )
