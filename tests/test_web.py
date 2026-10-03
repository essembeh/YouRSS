import re

from bs4 import BeautifulSoup
from httpx import AsyncClient, BasicAuth
from pytest import mark


async def test_default(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 307
    assert resp.headers["Location"] == "/@CardMagicByJason,@JonnyGiger"


async def test_watch(client: AsyncClient) -> None:
    resp = await client.get("/watch?v=q5IMA244HXw")
    assert resp.status_code == 307

    assert resp.headers["Location"] == "https://www.youtube-nocookie.com/embed/q5IMA244HXw?autoplay=1"


async def test_user(client: AsyncClient) -> None:
    # Alice's password is bar
    resp = await client.get("/u/alice")
    assert resp.status_code == 401

    resp = await client.get("/u/alice", auth=BasicAuth("4l1c3", "password"))
    assert resp.status_code == 401

    resp = await client.get("/u/alice", auth=BasicAuth("alice", "password"))
    assert resp.status_code == 401

    resp = await client.get("/u/alice", auth=BasicAuth("alice", "foo"))
    assert resp.status_code == 200

    # Demo has no password
    resp = await client.get("/u/demo")
    assert resp.status_code == 200

    # Unknown page
    resp = await client.get("/u/unknown")
    assert resp.status_code == 404


async def test_page_content(client: AsyncClient) -> None:
    names = [
        "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk",  # a playlist
        "UCVooVnzQxPSTXTMzSi1s6uw",  # a channel
        "@CardMagicByJason",  # a user
    ]
    resp = await client.get("/" + ",".join(names))
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 30


async def test_page_content_invalid_names(client: AsyncClient) -> None:
    names = [
        "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk",  # a playlist
        "UCVooVnzQxPSTXTMzSi1s6uw",  # a channel
        "@CardMagicByJason",  # a user
        "@UCAAAAAAAAAAAAAAAAAAAAAA",  # an unknown user
        "UCAAAAAAAAAAAAAAAAAAAAAA",  # an invalid channel
        "foobar",  # an invalid name
    ]
    resp = await client.get("/" + ",".join(names))
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 30


@mark.parametrize(
    "name,http_status",
    [
        ("UCVooVnzQxPSTXTMzSi1s6uw", 200),  # a channel
        ("@CardMagicByJason", 200),  # a user
        ("@UCAAAAAAAAAAAAAAAAAAAAAA", 404),  # an unknown user
        ("UCAAAAAAAAAAAAAAAAAAAAAA", 404),  # an invalid channel
        ("foo", 422),  # an invalid name
    ],
)
async def test_single_channel(client: AsyncClient, name: str, http_status: int) -> None:
    resp = await client.get(f"/c/{name}")
    assert resp.status_code == http_status


async def test_htmx_channel_tabs(client: AsyncClient) -> None:
    # @JonnyGiger publishes videos and shorts but has no live stream tab
    channel = "UCVooVnzQxPSTXTMzSi1s6uw"

    resp = await client.get(f"/htmx/channel/{channel}")
    assert resp.status_code == 200
    assert f"/htmx/videos/{channel}" in resp.text
    assert f"/htmx/streams/{channel}" not in resp.text

    resp = await client.get(f"/htmx/videos/{channel}")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 10

    # Youtube serves the channel home for a missing tab: it must render as an empty tab
    resp = await client.get(f"/htmx/streams/{channel}")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) == 0
    assert soup.find("div", class_="yourss-empty") is not None

    resp = await client.get(f"/htmx/playlists/{channel}")
    assert resp.status_code == 422
