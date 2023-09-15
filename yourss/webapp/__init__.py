from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import yourss

from .api import router as api_router
from .www import router as www_router

app = FastAPI(name=yourss.__name__, version=yourss.__version__)
app.include_router(www_router)
app.include_router(api_router, prefix="/api")
app.mount(
    "/static",
    StaticFiles(directory=Path(yourss.__file__).parent / "static"),
    name="static",
)
__all__ = ["app"]
