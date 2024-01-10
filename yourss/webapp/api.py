from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

import yourss

from ..cache import get_avatar_url, get_rssfeeds

router = APIRouter()


@router.get("/version")
async def version():
    return {"name": yourss.__name__, "version": yourss.__version__}


@router.get("/rss/{name}")
async def rss_feed(name: str) -> RedirectResponse:
    feed = get_rssfeeds([name]).get(name)
    if feed is None:
        raise HTTPException(status_code=404)
    return RedirectResponse(feed.url)


@router.get("/avatar/{name}")
async def avatar(name: str) -> RedirectResponse:
    url = get_avatar_url(name)
    if url is None:
        raise HTTPException(status_code=404)
    return RedirectResponse(url)
