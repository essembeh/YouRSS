from pathlib import Path

import environ
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from . import __file__ as rootdir
from . import __name__ as app_name
from . import __version__ as app_version
from .api import router as api_router
from .config import YOURSS_USERS, AppConfig
from .utils import parallel_fetch

TemplateResponse = Jinja2Templates(
    directory=Path(rootdir).parent / "templates"
).TemplateResponse

config = environ.to_config(AppConfig)

app = FastAPI(name=app_name, version=app_version)
app.include_router(api_router, prefix="/api")
app.mount(
    "/static", StaticFiles(directory=Path(rootdir).parent / "static"), name="static"
)


@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        app.url_path_for("view_channels", channels=config.DEFAULT_CHANNELS)
    )


@app.get("/{channels}", response_class=HTMLResponse)
async def view_channels(request: Request, channels: str):
    feeds = parallel_fetch(set(channels.split(",")))
    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "feeds": feeds,
            "config": config,
            "title": ", ".join(sorted((f.title for f in feeds))),
        },
    )


@app.get("/u/{user}", response_class=HTMLResponse)
async def get_user(request: Request, user: str):
    if user not in YOURSS_USERS:
        raise HTTPException(status_code=404, detail="User not found")

    feeds = parallel_fetch(set(YOURSS_USERS[user]))
    return TemplateResponse(
        "view.html",
        {"request": request, "feeds": feeds, "config": config, "title": f"/u/{user}"},
    )
