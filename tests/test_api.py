from httpx import AsyncClient

from yourss import __name__ as app_name
from yourss import __version__ as app_version


async def test_version(client: AsyncClient) -> None:
    resp = await client.get("/api/version")
    resp.raise_for_status()

    payload = resp.json()
    assert payload.get("name") == app_name
    assert payload.get("version") == app_version
