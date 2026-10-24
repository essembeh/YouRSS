import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.responses import Response
from starlette.types import Scope

from . import __name__ as app_name
from . import __version__ as app_version
from .routers import api, htmx, web
from .routers.jinja import template_page
from .security import UnknownUser
from .settings import current_config, iso_duration, static_folder
from .warmup import warm_forever, warm_interval


class CachedStaticFiles(StaticFiles):
    """Static files with a browser cache policy (the default one sends none)."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        out = await super().get_response(path, scope)
        # A versioned URL (?v=<mtime>, see static_url) never changes: cache it for good
        versioned = b"v=" in scope.get("query_string", b"")
        out.headers["Cache-Control"] = "public, max-age=31536000, immutable" if versioned else "public, max-age=3600"
        return out


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """The warm-up task runs for the life of the application, when enabled."""
    task = None
    if current_config.warmup_enabled and not current_config.cache_enabled:
        logger.warning("YOURSS_WARMUP_ENABLED is set but the cache is disabled: nothing to warm up")
    elif current_config.warmup_enabled:
        interval = warm_interval(current_config.cache_rss_ttl)
        logger.info("Warm-up of every page every {}", iso_duration(interval))
        task = asyncio.create_task(warm_forever(interval))
    yield
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def unknown_user(request: Request, error: UnknownUser) -> Response:
    """An unknown user is a page, like an unknown folder or page, not a JSON detail."""
    return template_page(
        request,
        "pages/error.jinja-html",
        status_code=404,
        title="This user does not exist",
        message="No user of this instance has this address.",
        home_link=True,
    )


def create_app(*, api_docs: bool) -> FastAPI:
    """The application, with or without the generated API documentation."""
    out = FastAPI(
        title=app_name,
        version=app_version,
        lifespan=lifespan,
        docs_url="/docs" if api_docs else None,
        redoc_url="/redoc" if api_docs else None,
        openapi_url="/openapi.json" if api_docs else None,
    )
    out.add_exception_handler(UnknownUser, unknown_user)  # type: ignore[arg-type]
    # A folder of videos is a few hundred kB of HTML, twenty times less once compressed
    out.add_middleware(GZipMiddleware, minimum_size=1000)
    out.include_router(web.router)
    out.include_router(htmx.router)
    out.include_router(api.router)
    out.mount("/static", CachedStaticFiles(directory=static_folder), name="static")
    return out


app = create_app(api_docs=current_config.api_docs_enabled)
