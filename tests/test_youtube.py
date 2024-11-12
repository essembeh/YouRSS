from http.cookiejar import CookieJar

import pytest
from httpx import AsyncClient

from yourss.youtube import (
    YoutubeMetadata,
    YoutubeRssApi,
    YoutubeWebApi,
)
from yourss.youtube.scrapper import VideoScrapper
from yourss.youtube.utils import bs_parse


@pytest.mark.asyncio(loop_scope="module")
async def test_rgpd():
    api = YoutubeWebApi()

    url = "/@jonnygiger"

    resp = await api.get_html(url)
    assert resp.status_code == 200
    assert (
        len(
            bs_parse(resp.text).find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
        )
        == 0
    )

    resp = await api.get_html(url, ucbcb=0)
    assert resp.status_code == 200
    assert (
        len(
            bs_parse(resp.text).find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
        )
        > 0
    )


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


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_videos():
    scrapper = VideoScrapper(YoutubeWebApi())

    page_iterator = scrapper.iter_videos("UCVooVnzQxPSTXTMzSi1s6uw")
    page1 = await anext(page_iterator)
    assert len(page1) == 30
    page2 = await anext(page_iterator)
    assert len(page2) > 10
    assert page1 != page2
