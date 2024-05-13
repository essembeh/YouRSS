import pytest_asyncio
from fastapi.testclient import TestClient

from yourss.cache import NoCache
from yourss.main import app
from yourss.youtube import YoutubeWebClient


@pytest_asyncio.fixture
async def yt_client():
    yield YoutubeWebClient(cache=NoCache())


@pytest_asyncio.fixture
async def yourss_client():
    yield TestClient(app)
