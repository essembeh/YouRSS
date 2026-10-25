from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from loguru import logger
from pydantic import ValidationError
from starlette.responses import HTMLResponse, Response
from starlette.status import (
    HTTP_303_SEE_OTHER,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from ..async_utils import async_fetch
from ..schema import Page, User, UsersConfig
from ..security import (
    LOGIN_COOKIE,
    UnknownUser,
    find_page,
    find_user,
    get_auth_user,
    login_token,
    read_config,
    verify_password,
)
from ..settings import current_config, static_folder
from ..youtube import YoutubeApi
from .jinja import template_page
from .schema import SUBSCRIPTIONS, SUBSCRIPTIONS_PATTERN, TOO_MANY, ChannelId
from .utils import canonical_names, folder_link_prefix, page_context

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
        # The browser then loads the image from Youtube: nothing is relayed. It keeps the redirect as long as the
        # server keeps the metadata, so it does not ask again for an avatar the server would not look up again
        max_age = int(current_config.cache_metadata_ttl.total_seconds())
        return RedirectResponse(channel.avatar, headers={"Cache-Control": f"public, max-age={max_age}"})
    # A failure is retried later, without hammering Youtube
    initial = n or (channel.name[:1] if channel is not None else "") or "?"
    return Response(initial_svg(initial), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/apple-touch-icon.png", response_class=FileResponse)
@router.get("/apple-touch-icon-precomposed.png", response_class=FileResponse)
async def apple_touch_icon() -> FileResponse:
    """The home screen icon, where iOS looks for it when it cannot read the page (a page behind a password)."""
    return FileResponse(
        static_folder / "icons" / "apple-touch-icon.png", headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/p/{page}", response_class=HTMLResponse)
async def page_of_the_file(request: Request, found: Page | None = Depends(find_page)) -> HTMLResponse:
    """A page of the users file, flat (docs/specs/pages-users.md §7); hidden or unknown, it does not exist."""
    if found is None:
        return template_page(
            request,
            "pages/error.jinja-html",
            status_code=HTTP_404_NOT_FOUND,
            title="This page does not exist",
            message="No page of this instance has this address.",
            home_link=True,
        )
    statuses = await async_fetch(found.channels, api=YoutubeApi())
    names = canonical_names(statuses)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=f"/p/{found.name}",
        **page_context(statuses),
        # A page is read-only: it only offers its multi channel copy
        copy_url="/" + ",".join(names) if current_config.custom_pages_enabled else None,
    )


def login_page(request: Request, user: User, *, error: bool = False) -> HTMLResponse:
    """The login form of a protected user, with a 401 and no Basic challenge (docs/specs/login.md §1)."""
    return template_page(
        request,
        "pages/login.jinja-html",
        status_code=HTTP_401_UNAUTHORIZED,
        title=f"/u/{user.name}",
        home_path="/",
        user_name=user.name,
        error=error,
    )


@router.post("/u/{username}", response_model=None)
@router.post("/u/{username}/{page}", response_model=None)
async def user_login(
    request: Request,
    user: User | None = Depends(find_user),
    password: Annotated[str, Form()] = "",
    logout: Annotated[str, Form()] = "",
) -> Response:
    """The login form posts to the page it protects, the answer goes back to it (docs/specs/login.md §2, §7)."""
    if user is None:
        raise UnknownUser()
    if logout:
        out = RedirectResponse(f"/u/{user.name}", status_code=HTTP_303_SEE_OTHER)
        out.delete_cookie(LOGIN_COOKIE, path=f"/u/{user.name}", httponly=True, samesite="lax")
        return out
    back = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    if user.password is None:
        return RedirectResponse(back, status_code=HTTP_303_SEE_OTHER)
    if not verify_password(user, password):
        logger.warning("Wrong login password for {} from {}", user.name, request.client and request.client.host)
        return login_page(request, user, error=True)
    out = RedirectResponse(back, status_code=HTTP_303_SEE_OTHER)
    out.set_cookie(
        LOGIN_COOKIE,
        login_token(user),
        max_age=int(current_config.login_ttl.total_seconds()),
        path=f"/u/{user.name}",
        secure=request.url.scheme == "https",
        httponly=True,
        samesite="lax",
    )
    return out


@router.get("/u/{username}", response_class=HTMLResponse)
async def user_tree(request: Request, user: User = Depends(get_auth_user)) -> HTMLResponse:
    """The folders of a user, none open: the script opens the last one shown, else the first (§6)."""
    return template_page(
        request,
        "pages/view.jinja-html",
        title=f"/u/{user.name}",
        user_name=user.name,
        folders=user.pages,
        protected=user.password is not None,
    )


@router.get("/u/{username}/{page}", response_class=HTMLResponse)
async def user_folder(
    request: Request,
    page: str,
    user: User = Depends(get_auth_user),
    config: UsersConfig | None = Depends(read_config),
    hx_request: Annotated[str | None, Header()] = None,
) -> HTMLResponse:
    """A folder of a user: the page, or with the header htmx sends its fragment (§3), hidden pages included."""
    folder = user.page(page)
    found = config.page(page) if folder is not None and config is not None else None
    if folder is None or found is None:
        if hx_request == "true":
            raise HTTPException(HTTP_404_NOT_FOUND)
        return template_page(
            request,
            "pages/error.jinja-html",
            status_code=HTTP_404_NOT_FOUND,
            title="This folder does not exist",
            message=f"The user /u/{user.name} has no such folder.",
            home_link=True,
        )
    statuses = await async_fetch(found.channels, api=YoutubeApi())
    return template_page(
        request,
        "partials/folder.jinja-html" if hx_request == "true" else "pages/view.jinja-html",
        title=f"/u/{user.name}",
        link_prefix=folder_link_prefix(user.name, folder.name),
        user_name=user.name,
        folders=user.pages,
        protected=user.password is not None,
        folder=folder,
        **page_context(statuses),
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
    context = page_context(statuses)
    return template_page(
        request,
        "pages/view.jinja-html",
        title=f"{len(ids)} subscription{'s' if len(ids) > 1 else ''}",
        title_sep=", ",
        **context,
        page_names=ids,
    )
