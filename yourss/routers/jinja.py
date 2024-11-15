from datetime import datetime
from typing import List

import arrow
from fastapi import Request
from jinja2 import Environment, FileSystemLoader
from starlette.templating import Jinja2Templates, _TemplateResponse

import yourss

from ..settings import current_config, templates_folder
from ..youtube import VideoDescription, YoutubeMetadata


def clean_title(text: str) -> str:
    if current_config.clean_titles:
        return text.capitalize()
    return text


def date_humanize(date: datetime | str) -> str:
    if isinstance(date, str):
        return date
    return arrow.get(date).humanize()


# Jinja customization
jinja_env = Environment(loader=FileSystemLoader(templates_folder))
jinja_env.filters["clean_title"] = clean_title
jinja_env.filters["date_humanize"] = date_humanize

jinja = Jinja2Templates(env=jinja_env)
TemplateResponse = jinja.TemplateResponse


def _template_page(template_name: str, request: Request, **kwargs) -> _TemplateResponse:
    return jinja.TemplateResponse(
        template_name,
        {
            "request": request,
            "version": yourss.__version__,
            "config": current_config,
            "theme": current_config.theme,
        }
        | {k: v for k, v in kwargs.items() if v is not None},
    )


def page_channel(request: Request, metadata: YoutubeMetadata) -> _TemplateResponse:
    return _template_page("pages/channel.jinja-html", request, metadata=metadata)


def tab_latest(request: Request, videos: List[VideoDescription]) -> _TemplateResponse:
    return _template_page("partials/tab.jinja-html", request, videos=videos)


def tab_videos(
    request: Request, videos: List[VideoDescription], next_page_url: str | None
) -> _TemplateResponse:
    return _template_page(
        "partials/tab.jinja-html",
        request,
        videos=videos,
        next_page_url=next_page_url,
    )


def tab_shorts(
    request: Request, videos: List[VideoDescription], next_page_url: str | None
) -> _TemplateResponse:
    return _template_page(
        "partials/tab.jinja-html",
        request,
        videos=videos,
        next_page_url=next_page_url,
    )


def next_page(
    request: Request, videos: List[VideoDescription], next_page_url: str | None
) -> _TemplateResponse:
    return _template_page(
        "partials/next-page.jinja-html",
        request,
        videos=videos,
        next_page_url=next_page_url,
    )
