import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from . import __file__ as rootdir
from . import __name__ as app_name
from . import __version__ as app_version
from .api import router as api_router
from .utils import parallel_fetch

TemplateResponse = Jinja2Templates(
    directory=Path(rootdir).parent / "templates"
).TemplateResponse

app = FastAPI(name=app_name, version=app_version)
app.include_router(api_router, prefix="/api")
app.mount(
    "/static", StaticFiles(directory=Path(rootdir).parent / "static"), name="static"
)


@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(app.url_path_for("view", channels="@jonnygiger"))


@app.get("/view/{channels}", response_class=HTMLResponse)
async def view(request: Request, channels: str):
    feeds = parallel_fetch(set(channels.split(",")))
    return TemplateResponse(
        "view.html",
        {"request": request, "feeds": feeds},
    )
