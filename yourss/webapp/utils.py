from typing import Generator

from ..cache import YoutubeWebClientWithCache
from ..youtube import YoutubeWebClient


def get_youtube_client() -> Generator[YoutubeWebClient, None, None]:
    client = YoutubeWebClientWithCache()
    yield client
