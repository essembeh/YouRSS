from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __name__ as app_name
from . import __version__ as app_version
from .routers import api, htmx, proxy, web
from .settings import static_folder

app = FastAPI(name=app_name, version=app_version)
app.include_router(web.router)
app.include_router(htmx.router)
app.include_router(api.router)
app.include_router(proxy.router)
app.mount("/static", StaticFiles(directory=static_folder), name="static")
