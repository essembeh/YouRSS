import pytest
from bs4 import BeautifulSoup
from httpx import get

from yourss.youtube import YoutubeApi


def is_rgpd_applicable():
    resp = get("https://ifconfig.io/country_code")
    return resp.status_code == 200 and resp.text.strip() == "FR"


@pytest.mark.skipif(not is_rgpd_applicable(), reason="Not applicable outside Europe")
@pytest.mark.asyncio(loop_scope="module")
async def test_rgpd():
    api = YoutubeApi()

    url = "/@jonnygiger"

    resp = await api.get_html(url)
    assert resp.status_code == 200
    assert (
        len(
            BeautifulSoup(resp.text, features="html.parser").find_all(
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
            BeautifulSoup(resp.text, features="html.parser").find_all(
                "form",
                attrs={"method": "POST", "action": "https://consent.youtube.com/save"},
            )
        )
        > 0
    )


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_channel():
    api = YoutubeApi()

    feed = await api.get_channel_rss("UCVooVnzQxPSTXTMzSi1s6uw")
    assert feed.title == "Jonny Giger"


@pytest.mark.asyncio(loop_scope="module")
async def test_rss_playlist():
    api = YoutubeApi()

    feed = await api.get_playlist_rss("PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk")
    assert feed.title == "IMPOSSIBLE TRICKS OF RODNEY MULLEN"


@pytest.mark.asyncio(loop_scope="module")
async def test_metadata_channel():
    api = YoutubeApi()

    page = await api.get_homepage("UCVooVnzQxPSTXTMzSi1s6uw")
    channel = page.get_metadata()
    assert channel.name == "Jonny Giger"
    assert channel.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.home == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.avatar is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_metadata_user():
    api = YoutubeApi()

    page = await api.get_homepage("@jonnygiger")
    channel = page.get_metadata()
    assert channel.name == "Jonny Giger"
    assert channel.channel_id == "UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.home == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    assert channel.avatar is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_scrap_videos():
    api = YoutubeApi()

    page_iterator = api.iter_videos("UCVooVnzQxPSTXTMzSi1s6uw")
    page1 = await anext(page_iterator)
    assert len(page1) == 30
    page2 = await anext(page_iterator)
    assert len(page2) > 10
    assert page1 != page2
