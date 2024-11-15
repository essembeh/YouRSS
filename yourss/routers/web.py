import json
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from ..async_utils import afetch_feeds
from ..schema import Theme, User
from ..security import get_auth_user
from ..settings import current_config
from ..youtube import Feed, PageScrapper, VideoDescription, VideoScrapper, YoutubeApi
from .jinja import (
    _template_page,
    next_page,
    page_channel,
    tab_latest,
    tab_shorts,
    tab_videos,
)
from .schema import ChannelId, UserId
from .utils import next_page_url, parse_channel_names

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("rss_channels", channels=current_config.default_channels)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(
        f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1&control=2&rel=0"
    )


@router.get("/user/{username}", response_class=HTMLResponse)
@router.get("/u/{username}", response_class=HTMLResponse)
async def rss_user(request: Request, user: User = Depends(get_auth_user)):
    api = YoutubeApi()
    feeds = await afetch_feeds(user.channels, api=api)
    active_feeds = [f for f in feeds.values() if isinstance(f, Feed)]
    if len(active_feeds) == 0:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No channels found")

    videos = []
    for feed in active_feeds:
        for entry in feed.entries:
            videos.append(
                VideoDescription(
                    video_id=entry.video_id,
                    title=entry.title,
                    published=entry.published,
                    channel=feed.title,
                    channel_id=feed.channel_id,
                    feed_uid=feed.uid,
                )
            )
    return _template_page(
        "pages/rss.jinja-html",
        request,
        title=f"/u/{user.name}",
        feeds=active_feeds,
        videos=videos,
        theme=user.theme,
    )


@router.get("/page/{channels}", response_class=HTMLResponse)
@router.get("/p/{channels}", response_class=HTMLResponse)
@router.get("/{channels}", response_class=HTMLResponse)
async def rss_channels(request: Request, channels: str):
    api = YoutubeApi()
    feeds = await afetch_feeds(parse_channel_names(channels), api=api)

    # check that all feeds have been fetched
    active_feeds = []
    videos = []
    for key, value in feeds.items():
        if isinstance(value, BaseException):
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching {key}: {value}",
            )
        else:
            active_feeds.append(value.title)
            for entry in value.entries:
                videos.append(
                    VideoDescription(
                        video_id=entry.video_id,
                        title=entry.title,
                        published=entry.published,
                        channel=value.title,
                        channel_id=value.channel_id,
                        feed_uid=value.uid,
                    )
                )

    return _template_page(
        "pages/rss.jinja-html",
        request,
        title=", ".join(sorted(active_feeds)),
        feeds=feeds.values(),
        videos=videos,
    )


@router.get("/channel/{channel}", response_class=HTMLResponse)
@router.get("/c/{channel}", response_class=HTMLResponse)
async def channel_home(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = PageScrapper.from_response(await api.get_homepage(channel))
    metadata = homepage.get_metadata()

    return page_channel(request, metadata=metadata)


@router.get("/channel/{channel}/latest", response_class=HTMLResponse)
async def channel_home_latest(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    feed = await api.get_channel_rss(channel)
    videos = [
        VideoDescription(
            video_id=e.video_id,
            title=e.title,
            published=e.published,
        )
        for e in feed.entries
    ]
    return tab_latest(request=request, videos=videos)


@router.get("/channel/{channel}/videos", response_class=HTMLResponse)
async def channel_home_videos(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = PageScrapper.from_response(
        await api.get_homepage(channel, suffix="/videos")
    )
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None
    out = tab_videos(
        request=request,
        videos=list(browse_data.iter_videos()),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=False),
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/channel/{channel}/streams", response_class=HTMLResponse)
async def channel_home_streams(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = PageScrapper.from_response(
        await api.get_homepage(channel, suffix="/streams")
    )
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None
    out = tab_videos(
        request=request,
        videos=list(browse_data.iter_videos()),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=False),
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/channel/{channel}/shorts", response_class=HTMLResponse)
async def channel_home_shorts(
    request: Request, channel: ChannelId | UserId, theme: Theme | None = None
):
    api = YoutubeApi()
    homepage = PageScrapper.from_response(
        await api.get_homepage(channel, suffix="/shorts")
    )
    assert (client_data := homepage.find_client_data()) is not None
    assert (browse_data := homepage.find_browse_data()) is not None
    out = tab_shorts(
        request=request,
        videos=list(browse_data.iter_videos(shorts=True)),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=True),
    )
    out.set_cookie("client_data", json.dumps(client_data))
    return out


@router.get("/htmx/next", response_class=HTMLResponse)
async def next(
    request: Request,
    client_data: Annotated[str, Cookie()],
    click_tracking_params: Annotated[str, Query()],
    continuation_token: Annotated[str, Query()],
    shorts: Annotated[bool, Query()] = False,
):
    browse_data = await VideoScrapper().get_next_page(
        json.loads(client_data), click_tracking_params, continuation_token
    )
    return next_page(
        request,
        videos=list(browse_data.iter_videos(shorts=shorts)),
        next_page_url=next_page_url(browse_data, "/htmx/next", shorts=shorts),
    )
