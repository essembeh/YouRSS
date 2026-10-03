from datetime import datetime

import arrow
from fastapi import Request
from jinja2 import Environment, FileSystemLoader
from starlette.templating import Jinja2Templates, _TemplateResponse

import yourss

from ..settings import current_config, static_folder, templates_folder


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
    version = int(file.stat().st_mtime) if file.exists() else yourss.__version__
    return f"/static/{path}?v={version}"


# Jinja customization
jinja_env = Environment(loader=FileSystemLoader(templates_folder), autoescape=True)
jinja_env.filters["clean_title"] = clean_title
jinja_env.filters["date_humanize"] = date_humanize
jinja_env.globals["static_url"] = static_url

jinja = Jinja2Templates(env=jinja_env)


def template_page(request: Request, template_name: str, **kwargs) -> _TemplateResponse:
    return jinja.TemplateResponse(
        request,
        template_name,
        context={
            "request": request,
            "version": yourss.__version__,
        }
        | {k: v for k, v in kwargs.items() if v is not None},
    )
