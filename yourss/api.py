from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from . import __name__ as app_name
from . import __version__ as app_version
from .model import RssFeed
from .schema import Feed
from .youtube import YoutubeScrapper, youtube_fetch_rss_feed, yt_home_url, yt_html_get

router = APIRouter()


@router.get("/version")
async def version():
    return {"name": app_name, "version": app_version}


@router.get("/rss/{name}")
async def rss_feed(name: str) -> Response:
    resp = youtube_fetch_rss_feed(name)
    resp.raise_for_status()
    return Response(resp.text, media_type=resp.headers.get("content-type"))


@router.get("/json/{name}")
async def json_feed(name: str) -> Feed:
    resp = youtube_fetch_rss_feed(name)
    feed = RssFeed.fromresponse(resp)
    return Feed.model_validate(feed)


@router.get("/avatar/{name}")
async def avatar(name: str) -> RedirectResponse:
    metadata = YoutubeScrapper.fromresponse(yt_html_get(yt_home_url(magic=name)))
    assert metadata.avatar_url is not None
    return RedirectResponse(metadata.avatar_url, status_code=301)
