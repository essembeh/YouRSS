from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_404_NOT_FOUND

from .. import __name__ as app_name
from .. import __version__ as app_version
from ..youtube import YoutubeWebClient
from .utils import force_https, get_youtube_client

router = APIRouter()


@router.get("/version")
async def version():
    return {"name": app_name, "version": app_version}


@router.get("/rss/{name}", response_class=RedirectResponse)
async def rss_feed(
    name: str, yt_client: Annotated[YoutubeWebClient, Depends(get_youtube_client)]
):
    feed = await yt_client.get_rss_feed(name)
    return RedirectResponse(force_https(str(feed.get_url())))


@router.get("/avatar/{name}", response_class=RedirectResponse)
async def avatar(
    name: str, yt_client: Annotated[YoutubeWebClient, Depends(get_youtube_client)]
):
    url = await yt_client.get_avatar_url(name)
    if url is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    return RedirectResponse(url)
