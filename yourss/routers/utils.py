from http.cookiejar import CookieJar
from typing import AsyncGenerator, Callable, List

from httpx import AsyncClient
from starlette.templating import Jinja2Templates, _TemplateResponse

cookiejar = CookieJar()


async def get_youtube_web_client() -> AsyncGenerator[AsyncClient, None]:
    yield AsyncClient(cookies=cookiejar)


def force_https(url: str) -> str:
    assert isinstance(url, str)
    if url.startswith("http:"):
        return url.replace("http:", "https:", 1)
    return url


def parse_channel_names(text: str, delimiter: str = ",") -> List[str]:
    return list(
        set(filter(lambda s: len(s) > 0, map(str.strip, text.split(delimiter))))
    )


def custom_template_response(
    jinja: Jinja2Templates, template_file: str, **kwargs
) -> Callable[..., _TemplateResponse]:
    def func(**kwargs2) -> _TemplateResponse:
        kwargs2.update(kwargs)
        return jinja.TemplateResponse(template_file, kwargs2)

    return func
