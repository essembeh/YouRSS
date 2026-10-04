from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPError
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_CONTENT

from .. import __name__ as app_name
from .. import __version__ as app_version
from ..settings import current_config
from ..youtube import ScrapingError, YoutubeApi, parse_channel_reference, parse_video_reference

router = APIRouter(prefix="/api")


@router.get("/version")
async def version() -> dict[str, str]:
    return {"name": app_name, "version": app_version}


async def _channel_name(api: YoutubeApi, text: str) -> str | None:
    # Only ids and handles taken from the text reach Youtube, never the address itself
    if (name := parse_channel_reference(text)) is not None:
        return name
    if (video_id := parse_video_reference(text)) is not None:
        return await api.get_video_channel(video_id)
    return None


@router.get("/resolve")
async def resolve(q: Annotated[str, Query(min_length=1, max_length=200)]) -> dict[str, str]:
    """Resolve what a visitor typed to a channel (docs/specs/custom-pages.md)."""
    if not current_config.custom_pages_enabled:
        raise HTTPException(HTTP_403_FORBIDDEN, detail="Custom pages are disabled on this instance")
    api = YoutubeApi()
    try:
        name = await _channel_name(api, q)
        if name is None:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Type a handle (@name), a channel_id, or the address of a channel or of a video",
            )
        out = await api.get_channel(name)
    except (HTTPError, ScrapingError) as error:
        raise HTTPException(HTTP_404_NOT_FOUND, detail=f"Nothing found for {q.strip()}") from error
    return {"kind": "channel", "id": out.channel_id, "name": out.name}
