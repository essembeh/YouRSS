from http.cookiejar import CookieJar

import pytest
from httpx import AsyncClient, get

from yourss.youtube import (
    YoutubeMetadata,
    YoutubeRssApi,
    YoutubeWebApi,
)
from yourss.youtube.utils import html_get_rgpd_forms


def is_rgpd_applicable():
    resp = get("https://ifconfig.io/country_code")
    return resp.status_code == 200 and resp.text.strip() == "FR"


@pytest.mark.skipif(not is_rgpd_applicable(), reason="Not applicable outside Europe")
@pytest.mark.asyncio(loop_scope="module")
async def test_rgpd_with_cookies():
    api = YoutubeWebApi(AsyncClient(cookies=CookieJar()))

    url = "https://www.youtube.com/@jonnygiger"

    # first call should fail
    resp = await api.get_html(url)
    assert resp.status_code == 200
    assert len(html_get_rgpd_forms(resp.text)) > 0

    # this call automatically accept the rgpd form
    resp = await api.get_rgpd_html(url)
    assert resp.status_code == 200
    assert len(html_get_rgpd_forms(resp.text)) == 0

    # now we can get the page without the rgpd form
    resp = await api.get_html(url)
    assert resp.status_code == 200
    assert len(html_get_rgpd_forms(resp.text)) == 0


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_channel():
    api = YoutubeRssApi()

    feed = await api.get_channel_rss("UCVooVnzQxPSTXTMzSi1s6uw")
    assert feed.title == "Jonny Giger"


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_playlist():
    api = YoutubeRssApi()

    feed = await api.get_playlist_rss("PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk")
    assert feed.title == "IMPOSSIBLE TRICKS OF RODNEY MULLEN"


@pytest.mark.asyncio(loop_scope="module")
async def test_metadata_channel():
    api = YoutubeWebApi(AsyncClient(cookies=CookieJar()))

    resp = await api.get_homepage("UCVooVnzQxPSTXTMzSi1s6uw")
    meta = YoutubeMetadata.from_response(resp)
    assert meta.title == "Jonny Giger"
    assert meta.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert (
        meta.url.geturl() == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    )
    assert meta.avatar_url is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_metadata_user():
    api = YoutubeWebApi(AsyncClient(cookies=CookieJar()))

    resp = await api.get_homepage("@jonnygiger")
    meta = YoutubeMetadata.from_response(resp)
    assert meta.title == "Jonny Giger"
    assert meta.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert (
        meta.url.geturl() == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    )
    assert meta.avatar_url is not None
