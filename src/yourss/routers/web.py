from html import escape
from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from loguru import logger
from pydantic import ValidationError
from starlette.responses import HTMLResponse, Response
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_CONTENT

from ..async_utils import SubscriptionStatus, async_fetch
from ..schema import User
from ..security import get_auth_user
from ..settings import current_config, static_folder
from ..youtube import VideoDescription, YoutubeApi
from .jinja import template_page
from .schema import SUBSCRIPTIONS, SUBSCRIPTIONS_PATTERN, TOO_MANY, ChannelId
from .utils import FetchSummary, canonical_names, fetch_summary, get_videos_from_feeds, page_entries

router = APIRouter()


def custom_pages_disabled(request: Request) -> HTMLResponse:
    """Error page of the home and of the multi channel pages when the administrator forbids them."""
    return template_page(
        request,
        "pages/error.jinja-html",
        status_code=HTTP_403_FORBIDDEN,
        title="Custom pages are disabled",
        message="The administrator of this instance does not let visitors build their own page.",
    )


@router.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    if not current_config.custom_pages_enabled:
        return custom_pages_disabled(request)
    # The home page is the tutorial: an editable page without any channel yet
    return template_page(request, "pages/home.jinja-html", title="Home", page_names=[])


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)) -> RedirectResponse:
    return RedirectResponse(f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1")


def initial_svg(letter: str) -> str:
    """The avatar of a channel Youtube did not give one for: its initial on a disc."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="32" fill="#2a3140"/>'
        '<text x="32" y="32" dy=".35em" text-anchor="middle" font-family="system-ui, sans-serif" font-size="30" '
        f'font-weight="700" fill="#aab3c5">{escape(letter.upper())}</text></svg>'
    )


@router.get("/avatar/{channel_id}", response_model=None)
async def avatar(channel_id: ChannelId, n: Annotated[str, Query(max_length=1)] = "") -> Response:
    """Redirect to the avatar of a channel on Youtube's CDN, else its initial (docs/specs/fetch-errors.md §1)."""
    try:
        channel = await YoutubeApi().get_channel(channel_id)
    except Exception as error:
        logger.warning("Could not get the avatar of {}: {!r}", channel_id, error)
        channel = None
    if channel is not None and channel.avatar:
        # The browser then loads the image from Youtube: nothing is relayed
        return RedirectResponse(channel.avatar, headers={"Cache-Control": "public, max-age=86400"})
    # A failure is retried later, without hammering Youtube
    initial = n or (channel.name[:1] if channel is not None else "") or "?"
    return Response(initial_svg(initial), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


class PageContext(TypedDict):
    """What the view template gets from the statuses: sidebar entries, videos, notice."""

    entries: list[SubscriptionStatus]
    videos: list[VideoDescription]
    summary: FetchSummary | None


def _page_context(statuses: list[SubscriptionStatus]) -> PageContext:
    feeds = [s.feed for s in statuses if s.feed is not None]
    channels = {s.channel.channel_id: s.channel for s in statuses if s.channel is not None}
    return {
        "entries": page_entries(statuses),
        "videos": get_videos_from_feeds(feeds, channels),
        "summary": fetch_summary(statuses),
    }


@router.get("/apple-touch-icon.png", response_class=FileResponse)
@router.get("/apple-touch-icon-precomposed.png", response_class=FileResponse)
async def apple_touch_icon() -> FileResponse:
    """The home screen icon, where iOS looks for it when it cannot read the page (a page behind a password)."""
    return FileResponse(
        static_folder / "icons" / "apple-touch-icon.png", headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/u/{username}", response_class=HTMLResponse)
async def user(request: Request, user: User = Depends(get_auth_user)) -> HTMLResponse:
    statuses = await async_fetch(user.channels, api=YoutubeApi())
    names = canonical_names(statuses)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=f"/u/{user.name}",
        **_page_context(statuses),
        # A user page is read-only: it only offers its multi channel copy
        copy_url="/" + ",".join(names) if current_config.custom_pages_enabled else None,
    )


@router.get("/{subscriptions}", response_class=HTMLResponse)
async def page(
    request: Request,
    subscriptions: Annotated[
        str,
        # Documented here, enforced below by the `Subscriptions` type so that a refusal is an HTML page
        Path(
            description=(
                "Channel ids and playlist ids, separated by commas. "
                f"At most {current_config.max_page_items} of them (YOURSS_MAX_PAGE_ITEMS)."
            ),
            examples=["UCVooVnzQxPSTXTMzSi1s6uw,PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"],
            json_schema_extra={"pattern": SUBSCRIPTIONS_PATTERN},
        ),
    ],
) -> HTMLResponse:
    if not current_config.custom_pages_enabled:
        return custom_pages_disabled(request)
    # Split and checked by the type, before anything is asked to Youtube
    try:
        ids = SUBSCRIPTIONS.validate_python(subscriptions)
    except ValidationError as error:
        if any(detail["type"] == TOO_MANY for detail in error.errors()):
            return template_page(
                request,
                "pages/error.jinja-html",
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                title="Too many subscriptions",
                message=f"A page of this instance holds at most {current_config.max_page_items} items.",
                home_link=True,
            )
        return template_page(
            request,
            "pages/error.jinja-html",
            status_code=HTTP_404_NOT_FOUND,
            title="This page does not exist",
            message=(
                "The address of a page holds channel ids and playlist ids, separated by commas. "
                "To add a channel by its handle or its address, use the form of the home page."
            ),
            home_link=True,
        )
    statuses = await async_fetch(ids, api=YoutubeApi())
    context = _page_context(statuses)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=", ".join(entry.label or entry.name for entry in context["entries"]),
        **context,
        page_names=ids,
    )
