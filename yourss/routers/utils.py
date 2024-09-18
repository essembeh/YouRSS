from typing import AsyncGenerator, Callable

from starlette.templating import Jinja2Templates, _TemplateResponse

from ..cache import create_cache
from ..settings import current_config
from ..youtube.client import YoutubeClient


def force_https(url: str) -> str:
    assert isinstance(url, str)
    if url.startswith("http:"):
        return url.replace("http:", "https:", 1)
    return url


async def get_youtube_client(
    refresh: bool = False,
) -> AsyncGenerator[YoutubeClient, None]:
    yield YoutubeClient(
        cache=await create_cache(
            redis_url=current_config.redis_url, force_renew=refresh
        )
    )


def parse_channel_names(text: str, delimiter: str = ",") -> set[str]:
    return set(filter(None, text.split(delimiter)))


def custom_template_response(
    jinja: Jinja2Templates, template_file: str, **kwargs
) -> Callable[..., _TemplateResponse]:
    def func(**kwargs2) -> _TemplateResponse:
        kwargs2.update(kwargs)
        return jinja.TemplateResponse(template_file, kwargs2)

    return func
