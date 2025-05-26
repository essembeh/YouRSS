import pytest
from bs4 import BeautifulSoup
from httpx import BasicAuth


@pytest.mark.anyio
async def test_default(client):
    resp = await client.get("/")
    assert resp.status_code == 307
    assert resp.headers["Location"] == "/@CardMagicByJason,@JonnyGiger"


@pytest.mark.anyio
async def test_watch(client):
    resp = await client.get("/watch?v=q5IMA244HXw")
    assert resp.status_code == 307

    assert resp.headers["Location"] == "/proxy/player/q5IMA244HXw"


@pytest.mark.anyio
async def test_user(client):
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


@pytest.mark.anyio
async def test_page_content(client):
    names = [
        "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk",  # a playlist
        "UCVooVnzQxPSTXTMzSi1s6uw",  # a channel
        "@CardMagicByJason",  # a user
    ]
    resp = await client.get("/" + ",".join(names))
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", class_="yourss-filterable")) == 45


@pytest.mark.anyio
async def test_page_content_invalid_names(client):
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
    assert len(soup.find_all("div", class_="yourss-filterable")) == 45


@pytest.mark.anyio
@pytest.mark.parametrize(
    "name,http_status",
    [
        ("UCVooVnzQxPSTXTMzSi1s6uw", 200),  # a channel
        ("@CardMagicByJason", 200),  # a user
        ("@UCAAAAAAAAAAAAAAAAAAAAAA", 404),  # an unknown user
        ("UCAAAAAAAAAAAAAAAAAAAAAA", 404),  # an invalid channel
        ("foo", 422),  # an invalid name
    ],
)
async def test_single_channel(client, name: str, http_status: int):
    resp = await client.get(f"/c/{name}")
    assert resp.status_code == http_status
