from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from starlette.responses import HTMLResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_CONTENT

from ..async_utils import async_fetch
from ..schema import User
from ..security import get_auth_user
from ..settings import current_config
from ..youtube import YoutubeApi
from .jinja import template_page
from .schema import SUBSCRIPTIONS, SUBSCRIPTIONS_PATTERN, TOO_MANY
from .utils import canonical_names, get_videos_from_feeds

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


@router.get("/u/{username}", response_class=HTMLResponse)
async def user(request: Request, user: User = Depends(get_auth_user)) -> HTMLResponse:
    api = YoutubeApi()
    channels, feeds, errors = await async_fetch(user.channels, api=api)
    videos = get_videos_from_feeds(feeds, channels)
    names = canonical_names(user.channels)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=f"/u/{user.name}",
        channels=sorted(channels.values(), key=lambda c: c.name.lower()),
        videos=videos,
        errors=errors,
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
    api = YoutubeApi()
    channels, feeds, errors = await async_fetch(ids, api=api)
    videos = get_videos_from_feeds(feeds, channels)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=", ".join(sorted((c.name for c in channels.values()), key=str.lower)),
        channels=sorted(channels.values(), key=lambda c: c.name.lower()),
        videos=videos,
        errors=errors,
        page_names=ids,
    )
