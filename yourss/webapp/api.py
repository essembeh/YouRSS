from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

import yourss

from ..model import RssFeed
from ..schema import Feed
from ..youtube import youtube_get_metadata, youtube_get_rss_feed

router = APIRouter()


@router.get("/version")
async def version():
    return {"name": yourss.__name__, "version": yourss.__version__}


@router.get("/rss/{name}")
async def rss_feed(name: str) -> RedirectResponse:
    resp = youtube_get_rss_feed(name)
    feed = RssFeed.fromresponse(resp)
    return RedirectResponse(feed.url)


@router.get("/json/{name}")
async def json_feed(name: str) -> Feed:
    resp = youtube_get_rss_feed(name)
    feed = RssFeed.fromresponse(resp)
    return Feed.model_validate(feed)


@router.get("/avatar/{name}")
async def avatar(name: str) -> RedirectResponse:
    metadata = youtube_get_metadata(name)
    if metadata.avatar_url is None:
        raise HTTPException(status_code=404)
    return RedirectResponse(metadata.avatar_url)
