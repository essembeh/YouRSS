from datetime import datetime

import arrow
from fastapi import Request
from jinja2 import Environment, FileSystemLoader
from starlette.templating import Jinja2Templates, _TemplateResponse

import yourss

from ..settings import current_config, templates_folder


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


def template_page(request: Request, template_name: str, **kwargs) -> _TemplateResponse:
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
