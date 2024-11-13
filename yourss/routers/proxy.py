from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import PositiveInt
from starlette.status import HTTP_404_NOT_FOUND

from ..youtube import (
    PageScrapper,
    YoutubeApi,
    is_channel_id,
    is_playlist_id,
    is_user,
)
from .schema import ChannelId, Playlist_Id, UserId
from .utils import force_https

router = APIRouter()


@router.get("/rss/{name}", response_class=RedirectResponse)
async def rss_feed(name: UserId | ChannelId | Playlist_Id):
    api = YoutubeApi()

    feed = None
    # if a user is provided, get the channel id
    if is_user(name):
        homepage = PageScrapper.from_response(await api.get_homepage(name))
        meta = homepage.get_metadata()
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
async def avatar(name: UserId | ChannelId):
    api = YoutubeApi()

    homepage = PageScrapper.from_response(await api.get_homepage(name))
    meta = homepage.get_metadata()

    if (url := meta.avatar_url) is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=f"Cannot find avatar for: {name}"
        )
    return RedirectResponse(url)


@router.get("/home/{name}", response_class=RedirectResponse)
async def home(name: UserId | ChannelId):
    api = YoutubeApi()

    homepage = PageScrapper.from_response(await api.get_homepage(name))
    meta = homepage.get_metadata()

    return RedirectResponse(meta.url)


@router.get("/thumbnail/{video_id}", response_class=RedirectResponse)
async def thumbnail(video_id: str, instance: PositiveInt = 1):
    return RedirectResponse(
        f"https://i{instance}.ytimg.com/vi/{video_id}/hqdefault.jpg"
    )
