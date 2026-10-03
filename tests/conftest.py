from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from pytest import fixture

from yourss.main import app


@fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as client:
        yield client
