from typing import Callable

from starlette.templating import Jinja2Templates, _TemplateResponse

from .config import current_config


def parse_channel_names(text: str, delimiter: str = ",") -> set[str]:
    return set(filter(None, text.split(delimiter)))


def custom_template_response(
    jinja: Jinja2Templates, template_file: str, **kwargs
) -> Callable[..., _TemplateResponse]:
    def func(**kwargs2) -> _TemplateResponse:
        kwargs2.update(kwargs)
        return jinja.TemplateResponse(template_file, kwargs2)

    return func


def clean_title(text: str) -> str:
    if current_config.CLEAN_TITLES:
        return text.capitalize()
    return text
