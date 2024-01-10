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
    feeds = await get_rssfeeds([name])
    if (feed := feeds.get(name)) is not None:
        return RedirectResponse(feed.url)
    raise HTTPException(status_code=404)


@router.get("/avatar/{name}")
async def avatar(name: str) -> RedirectResponse:
    url = await get_avatar_url(name)
    if url is not None:
        return RedirectResponse(url)
    raise HTTPException(status_code=404)
