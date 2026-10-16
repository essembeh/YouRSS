from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import arrow
from fastapi import Request
from jinja2 import Environment, FileSystemLoader
from starlette.status import HTTP_200_OK
from starlette.templating import Jinja2Templates, _TemplateResponse

from .. import __version__
from ..settings import current_config, static_folder, templates_folder
from .utils import age_text


def clean_title(text: str) -> str:
    if current_config.clean_titles:
        return text.capitalize()
    return text


def date_humanize(date: datetime | str | None) -> str:
    if date is None:
        return ""
    if isinstance(date, str):
        return date
    return arrow.get(date).humanize()


def static_url(path: str) -> str:
    # The mtime busts the browser cache as soon as an asset changes
    file = static_folder / path
    version = int(file.stat().st_mtime) if file.exists() else __version__
    return f"/static/{path}?v={version}"


# Jinja customization
jinja_env = Environment(loader=FileSystemLoader(templates_folder), autoescape=True)
jinja_env.filters["clean_title"] = clean_title
jinja_env.filters["date_humanize"] = date_humanize
jinja_env.filters["age_text"] = age_text
jinja_env.globals["static_url"] = static_url

jinja = Jinja2Templates(env=jinja_env)


def link_prefix(request: Request) -> str:
    """Start of a link to a channel of the page (`<prefix>c=<id>`): its path, and the folder named in the URL."""
    current = request.headers.get("hx-current-url")
    url = urlparse(current) if current else request.url
    # Only a local path may end in a link
    path = url.path if url.path.startswith("/") and not url.path.startswith("//") else "/"
    folder = parse_qs(url.query).get("f", [""])[0]
    return f"{path}?f={quote(folder)}&" if folder else f"{path}?"


def template_page(
    request: Request, template_name: str, *, status_code: int = HTTP_200_OK, **kwargs: Any
) -> _TemplateResponse:
    return jinja.TemplateResponse(
        request,
        template_name,
        context={
            "request": request,
            "link_prefix": link_prefix(request),
            "max_page_items": current_config.max_page_items,
            "version": __version__,
        }
        | {k: v for k, v in kwargs.items() if v is not None},
        status_code=status_code,
    )
