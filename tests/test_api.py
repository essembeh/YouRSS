import re

import pytest

from yourss.main import app_name, app_version


@pytest.mark.anyio
async def test_version(client):
    resp = await client.get("/api/version")
    resp.raise_for_status()

    payload = resp.json()
    assert payload.get("name") == app_name
    assert payload.get("version") == app_version


@pytest.mark.anyio
async def test_proxy_rss(client):
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
async def test_proxy_avatar(client):
    channel = await client.get("/proxy/avatar/UCVooVnzQxPSTXTMzSi1s6uw")
    user = await client.get("/proxy/avatar/@jonnygiger")

    assert user.status_code == channel.status_code == 307
    assert user.headers["Location"] == user.headers["Location"]
    assert re.fullmatch(
        r"^https://yt[0-9]+\.googleusercontent\.com/.*$", user.headers["Location"]
    )


@pytest.mark.anyio
async def test_proxy_home(client):
    channel = await client.get("/proxy/home/UCVooVnzQxPSTXTMzSi1s6uw")
    user = await client.get("/proxy/home/@jonnygiger")

    assert user.status_code == channel.status_code == 307
    assert (
        user.headers["Location"]
        == user.headers["Location"]
        == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    )


@pytest.mark.anyio
async def test_proxy_thumbnail(client):
    thumbnail = await client.get("/proxy/thumbnail/XivF3Nx3exA")
    thumbnail2 = await client.get("/proxy/thumbnail/XivF3Nx3exA?instance=2")
    assert thumbnail.status_code == thumbnail2.status_code == 307
    assert (
        thumbnail.headers["Location"]
        == "https://i1.ytimg.com/vi/XivF3Nx3exA/hqdefault.jpg"
    )
    assert (
        thumbnail2.headers["Location"]
        == "https://i2.ytimg.com/vi/XivF3Nx3exA/hqdefault.jpg"
    )
