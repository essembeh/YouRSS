from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from . import __name__ as app_name
from . import __version__ as app_version
from .routers import api, htmx, proxy, web
from .settings import current_config, static_folder


class CachedStaticFiles(StaticFiles):
    """Static files with a browser cache policy (the default one sends none)."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        out = await super().get_response(path, scope)
        # A versioned URL (?v=<mtime>, see static_url) never changes: cache it for good
        versioned = b"v=" in scope.get("query_string", b"")
        out.headers["Cache-Control"] = "public, max-age=31536000, immutable" if versioned else "public, max-age=3600"
        return out


def create_app(*, api_docs: bool) -> FastAPI:
    """The application, with or without the generated API documentation."""
    out = FastAPI(
        name=app_name,
        version=app_version,
        docs_url="/docs" if api_docs else None,
        redoc_url="/redoc" if api_docs else None,
        openapi_url="/openapi.json" if api_docs else None,
    )
    out.include_router(web.router)
    out.include_router(htmx.router)
    out.include_router(api.router)
    out.include_router(proxy.router)
    out.mount("/static", CachedStaticFiles(directory=static_folder), name="static")
    return out


app = create_app(api_docs=current_config.api_docs_enabled)
