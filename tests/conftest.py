import pytest_asyncio
from fastapi.testclient import TestClient

from yourss.main import app
from yourss.youtube.client import YoutubeClient


@pytest_asyncio.fixture
async def yt_client():
    yield YoutubeClient()


@pytest_asyncio.fixture
async def yourss_client():
    yield TestClient(app)
