import re

from bs4 import BeautifulSoup
from httpx import AsyncClient, BasicAuth
from pytest import MonkeyPatch, mark

from yourss.settings import current_config
from yourss.youtube import YoutubeApi


async def test_home(client: AsyncClient) -> None:
    # The home page is the tutorial: an editable page without any channel
    resp = await client.get("/")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None and soup.body["data-page-names"] == ""
    assert soup.find("form", class_="yourss-add-form") is not None


async def test_page_is_editable(client: AsyncClient) -> None:
    # Duplicates are dropped, the order is kept and a resolved handle becomes its id
    resp = await client.get("/@JonnyGiger,UCQsmxaMzYr76Yd1iqMEq8TA,@JonnyGiger")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None
    assert soup.body["data-page-names"] == "UCVooVnzQxPSTXTMzSi1s6uw,UCQsmxaMzYr76Yd1iqMEq8TA"
    assert len(soup.find_all("button", attrs={"data-action": "remove-channel"})) == 2


async def test_user_page_is_read_only(client: AsyncClient) -> None:
    resp = await client.get("/u/demo")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None and not soup.body.has_attr("data-page-names")
    assert soup.find("button", attrs={"data-action": "remove-channel"}) is None
    copy = soup.find("a", class_="yourss-copy-page")
    assert copy is not None and str(copy["href"]).startswith("/UC")


@mark.parametrize(
    "query,http_status",
    [
        ("UCVooVnzQxPSTXTMzSi1s6uw", 200),  # a channel id
        ("@JonnyGiger", 200),  # a handle
        ("https://www.youtube.com/@JonnyGiger/videos", 200),  # the address of a channel
        ("@UCAAAAAAAAAAAAAAAAAAAAAA", 404),  # an unknown handle
        ("https://youtu.be/AAAAAAAAAAA", 404),  # an unknown video
        ("jonny giger", 422),  # neither a handle, an id nor an address
    ],
)
async def test_api_channel(client: AsyncClient, query: str, http_status: int) -> None:
    resp = await client.get("/api/channel", params={"q": query})
    assert resp.status_code == http_status
    if http_status == 200:
        assert resp.json() == {"channel_id": "UCVooVnzQxPSTXTMzSi1s6uw", "name": "Jonny Giger"}


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


async def test_api_channel_from_video(client: AsyncClient) -> None:
    channel = "UCVooVnzQxPSTXTMzSi1s6uw"
    feed = await YoutubeApi().get_channel_rss(channel)
    video_id = feed.entries[0].to_video().video_id

    resp = await client.get("/api/channel", params={"q": f"https://www.youtube.com/watch?v={video_id}"})
    assert resp.status_code == 200
    assert resp.json()["channel_id"] == channel


async def test_custom_pages_disabled(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(current_config, "custom_pages_enabled", False)

    # The home page and the multi channel pages are an error page
    for path in ("/", "/UCVooVnzQxPSTXTMzSi1s6uw"):
        resp = await client.get(path)
        assert resp.status_code == 403
        assert "Custom pages are disabled" in resp.text
        assert "data-page-names" not in resp.text
    resp = await client.get("/api/channel", params={"q": "UCVooVnzQxPSTXTMzSi1s6uw"})
    assert resp.status_code == 403

    # User pages and single channel pages remain, without the way to a custom copy
    resp = await client.get("/u/demo")
    assert resp.status_code == 200
    assert "yourss-copy-page" not in resp.text
    resp = await client.get("/c/UCVooVnzQxPSTXTMzSi1s6uw")
    assert resp.status_code == 200
