from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from httpx import AsyncClient
from pydantic import PositiveInt
from starlette.status import HTTP_404_NOT_FOUND

from ..youtube import (
    YoutubeMetadata,
    YoutubeRssApi,
    YoutubeWebApi,
    is_channel_id,
    is_playlist_id,
    is_user,
)
from .schema import ChannelId, Playlist_Id, UserId
from .utils import force_https, get_youtube_web_client

router = APIRouter()


@router.get("/rss/{name}", response_class=RedirectResponse)
async def rss_feed(
    name: UserId | ChannelId | Playlist_Id,
    yt_client: AsyncClient = Depends(get_youtube_web_client),
):
    api = YoutubeRssApi()
    webapi = YoutubeWebApi(yt_client)

    feed = None
    # if a user is provided, get the channel id
    if is_user(name):
        homepage = await webapi.get_homepage(name)
        meta = YoutubeMetadata.from_response(homepage)
        name = meta.channel_id

    if is_channel_id(name):
        feed = await api.get_channel_rss(name)
    elif is_playlist_id(name):
        feed = await api.get_playlist_rss(name)

    if feed is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=f"Cannot find rss for: {name}"
        )
    return RedirectResponse(force_https(str(feed.get_url())))


@router.get("/avatar/{name}", response_class=RedirectResponse)
async def avatar(
    name: UserId | ChannelId, yt_client: AsyncClient = Depends(get_youtube_web_client)
):
    webapi = YoutubeWebApi(yt_client)

    homepage = await webapi.get_homepage(name)
    meta = YoutubeMetadata.from_response(homepage)

    if (url := meta.avatar_url) is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=f"Cannot find avatar for: {name}"
        )
    return RedirectResponse(url)


@router.get("/home/{name}", response_class=RedirectResponse)
async def home(
    name: UserId | ChannelId, yt_client: AsyncClient = Depends(get_youtube_web_client)
):
    webapi = YoutubeWebApi(yt_client)

    homepage = await webapi.get_homepage(name)
    meta = YoutubeMetadata.from_response(homepage)

    return RedirectResponse(meta.url.geturl())


@router.get("/thumbnail/{video_id}", response_class=RedirectResponse)
async def thumbnail(video_id: str, instance: PositiveInt = 1):
    return RedirectResponse(
        f"https://i{instance}.ytimg.com/vi/{video_id}/hqdefault.jpg"
    )
