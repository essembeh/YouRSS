import re

import pytest
from httpx import AsyncClient

from yourss import __name__ as app_name
from yourss import __version__ as app_version


@pytest.mark.anyio
async def test_version(client: AsyncClient) -> None:
    resp = await client.get("/api/version")
    resp.raise_for_status()

    payload = resp.json()
    assert payload.get("name") == app_name
    assert payload.get("version") == app_version


@pytest.mark.anyio
async def test_proxy_rss(client: AsyncClient) -> None:
    channel = await client.get("/proxy/rss/UCVooVnzQxPSTXTMzSi1s6uw")
    user = await client.get("/proxy/rss/@jonnygiger")
    playlist = await client.get("/proxy/rss/PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk")

    assert user.status_code == channel.status_code == playlist.status_code == 307
    assert (
        user.headers["Location"]
        == user.headers["Location"]
        == "https://www.youtube.com/feeds/videos.xml?channel_id=UCVooVnzQxPSTXTMzSi1s6uw"
    )
    assert (
        playlist.headers["Location"]
        == "https://www.youtube.com/feeds/videos.xml?playlist_id=PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"
    )


@pytest.mark.anyio
async def test_proxy_avatar(client: AsyncClient) -> None:
    channel = await client.get("/proxy/avatar/UCVooVnzQxPSTXTMzSi1s6uw")
    user = await client.get("/proxy/avatar/@jonnygiger")

    assert user.status_code == channel.status_code == 307
    assert user.headers["Location"] == user.headers["Location"]
    assert re.fullmatch(r"^https://yt[0-9]+\.googleusercontent\.com/.*$", user.headers["Location"])


@pytest.mark.anyio
async def test_proxy_home(client: AsyncClient) -> None:
    channel = await client.get("/proxy/home/UCVooVnzQxPSTXTMzSi1s6uw")
    user = await client.get("/proxy/home/@jonnygiger")

    assert user.status_code == channel.status_code == 307
    assert (
        user.headers["Location"]
        == user.headers["Location"]
        == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    )
