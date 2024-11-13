import pytest
from bs4 import BeautifulSoup
from httpx import BasicAuth


@pytest.mark.anyio
async def test_default(client):
    resp = await client.get("/")
    assert resp.status_code == 307
    assert resp.headers["Location"] == "/@CardMagicByJason"


@pytest.mark.anyio
async def test_watch(client):
    resp = await client.get("/watch?v=q5IMA244HXw")
    assert resp.status_code == 307
    assert (
        resp.headers["Location"]
        == "https://www.youtube-nocookie.com/embed/q5IMA244HXw?autoplay=1&control=2&rel=0"
    )


@pytest.mark.anyio
async def test_homepage(client):
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
        "@UCAAAAAAAAAAAAAAAAAAAAAA",  # an unknown user
        "UCAAAAAAAAAAAAAAAAAAAAAA",  # an invalid channel
        "foobar",  # an invalid name
    ]
    resp = await client.get("/" + ",".join(names))
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", class_="yourss-filterable")) == 45

    # when no valid feed given, should return 404
    resp = await client.get("/UCAAAAAAAAAAAAAAAAAAAAAA,@UCAAAAAAAAAAAAAAAAAAAAAA")
    assert resp.status_code == 404
