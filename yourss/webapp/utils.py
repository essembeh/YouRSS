from typing import AsyncGenerator

from ..cache import create_cache
from ..config import current_config
from ..youtube import YoutubeWebClient


async def get_youtube_client(
    refresh: bool = False,
) -> AsyncGenerator[YoutubeWebClient, None]:
    yield YoutubeWebClient(
        cache=await create_cache(
            redis_url=current_config.REDIS_URL, force_renew=refresh
        )
    )
