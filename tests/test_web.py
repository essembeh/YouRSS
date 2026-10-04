import re

from bs4 import BeautifulSoup
from httpx import AsyncClient, BasicAuth
from pytest import MonkeyPatch, mark

from yourss.settings import current_config
from yourss.youtube import YoutubeApi

# What htmx sends with each of its requests
HTMX = {"HX-Request": "true"}


async def test_home(client: AsyncClient) -> None:
    # The home page is the tutorial: an editable page without any channel
    resp = await client.get("/")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None and soup.body["data-page-names"] == ""
    assert soup.find("form", class_="yourss-add-form") is not None


async def test_page_is_editable(client: AsyncClient) -> None:
    # Duplicates are dropped and the order is kept
    resp = await client.get("/UCVooVnzQxPSTXTMzSi1s6uw,UCQsmxaMzYr76Yd1iqMEq8TA,UCVooVnzQxPSTXTMzSi1s6uw")
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
    # No application route in the links: everything points to Youtube
    assert "/proxy/" not in resp.text
    assert soup.find("button", attrs={"data-action": "remove-channel"}) is None
    copy = soup.find("a", class_="yourss-copy-page")
    assert copy is not None and str(copy["href"]).startswith("/UC")
    # A user page holds playlists too: listed, opened inside the page, not removable
    playlist = soup.find("li", class_="yourss-playlist")
    assert playlist is not None and playlist["data-playlist-id"] == "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"


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
async def test_api_resolve(client: AsyncClient, query: str, http_status: int) -> None:
    resp = await client.get("/api/resolve", params={"q": query})
    assert resp.status_code == http_status
    if http_status == 200:
        assert resp.json() == {"kind": "channel", "id": "UCVooVnzQxPSTXTMzSi1s6uw", "name": "Jonny Giger"}


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

    # /u/ is the only address of a user page
    resp = await client.get("/user/demo")
    assert resp.status_code == 404


async def test_page_content(client: AsyncClient) -> None:
    names = [
        "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk",  # a playlist
        "UCVooVnzQxPSTXTMzSi1s6uw",  # a channel
        "UCQsmxaMzYr76Yd1iqMEq8TA",  # another channel
    ]
    resp = await client.get("/" + ",".join(names))
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 30


async def test_page_content_invalid_names(client: AsyncClient) -> None:
    names = [
        "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk",  # a playlist
        "UCVooVnzQxPSTXTMzSi1s6uw",  # a channel
        "UCQsmxaMzYr76Yd1iqMEq8TA",  # another channel
        "UCAAAAAAAAAAAAAAAAAAAAAA",  # an unknown channel
        "PLAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # an unknown playlist
        "foobar",  # an invalid name
    ]
    # An item which is not an id: the address is not a page, nothing is fetched
    resp = await client.get("/" + ",".join(names))
    assert resp.status_code == 404
    assert "This page does not exist" in resp.text

    # Well formed but unknown ids only add an error to the page
    resp = await client.get("/" + ",".join(names[:-1]))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 30
    assert len(soup.find_all("div", class_="yourss-error")) == 2


@mark.parametrize("path", ["/foo", "/favicon.ico", "/robots.txt", "/foo,UCVooVnzQxPSTXTMzSi1s6uw"])
async def test_stray_path_is_not_a_page(client: AsyncClient, path: str) -> None:
    resp = await client.get(path)
    assert resp.status_code == 404


CHANNEL = "UCVooVnzQxPSTXTMzSi1s6uw"


@mark.parametrize(
    "path",
    [
        f"/{CHANNEL}<script>alert(1)</script>",
        f"/{CHANNEL}%22%20onload=%22alert(1)",  # an attribute injection
        f"/{CHANNEL}%0d%0aSet-Cookie:%20a=b",  # a header injection
        f"/{CHANNEL}%00",  # a null byte
        f"/{CHANNEL}%3Flist=x",  # an encoded query
        f"/{CHANNEL}%2F..%2Fsecret",  # an encoded path traversal
        "/UCVooVnzQxPSTXTMzSi1s6u",  # one character short
        "/ucvoovnzqxpstxtmzsi1s6uw",  # ids are case sensitive
        "/UCVooVnzQxPSTXTMzSi1s6u%D1%88",  # a letter of another alphabet in an id
        "/@JonnyGiger",  # a handle is resolved by the add form, never by an address
        f"/{CHANNEL},@JonnyGiger",
        f"/{CHANNEL};{CHANNEL}",  # the only separator is the comma
        f"/{CHANNEL},{CHANNEL} OR 1=1",
        "/" + "A" * 5000,
    ],
)
async def test_page_address_is_strict(client: AsyncClient, path: str, monkeypatch: MonkeyPatch) -> None:
    async def never_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("Youtube must not be asked anything for a refused address")

    monkeypatch.setattr(YoutubeApi, "get_channel", never_called)
    monkeypatch.setattr(YoutubeApi, "get_channel_rss", never_called)
    monkeypatch.setattr(YoutubeApi, "get_playlist_rss", never_called)

    resp = await client.get(path)
    assert resp.status_code in (404, 422)
    # Nothing of the address is echoed back
    assert "alert(1)" not in resp.text
    assert "set-cookie" not in resp.headers


async def test_page_address_documentation() -> None:
    from yourss.main import create_app

    schema = create_app(api_docs=True).openapi()
    (parameter,) = schema["paths"]["/{subscriptions}"]["get"]["parameters"]
    assert parameter["name"] == "subscriptions"
    assert parameter["schema"]["pattern"] == (
        "^(?:UC[A-Za-z0-9_-]{22}|PL[A-Za-z0-9_-]{32})(?:,(?:UC[A-Za-z0-9_-]{22}|PL[A-Za-z0-9_-]{32}))*$"
    )
    assert "YOURSS_MAX_PAGE_ITEMS" in parameter["description"]


async def test_page_items_are_limited(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    assert current_config.max_page_items == 12
    monkeypatch.setattr(current_config, "max_page_items", 2)
    channels = ["UCVooVnzQxPSTXTMzSi1s6uw", "UCQsmxaMzYr76Yd1iqMEq8TA", "UCBqd6fLWpemEM2o5wlNDUfw"]

    # Duplicates do not count
    resp = await client.get("/" + ",".join([*channels[:2], channels[0]]))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None and soup.body["data-page-max"] == "2"

    resp = await client.get("/" + ",".join(channels))
    assert resp.status_code == 422
    assert "at most 2" in resp.text

    # A user page is chosen by the administrator: it is not limited
    resp = await client.get("/u/demo")
    assert resp.status_code == 200


@mark.parametrize(
    "name,http_status",
    [
        ("UCVooVnzQxPSTXTMzSi1s6uw", 200),  # a channel
        ("@CardMagicByJason", 200),  # a user
        ("foo", 422),  # an invalid name
    ],
)
async def test_htmx_channel(client: AsyncClient, name: str, http_status: int) -> None:
    resp = await client.get(f"/htmx/channel/{name}", headers=HTMX)
    assert resp.status_code == http_status


async def test_htmx_channel_tabs(client: AsyncClient) -> None:
    # @JonnyGiger publishes videos and shorts but has no live stream tab
    channel = "UCVooVnzQxPSTXTMzSi1s6uw"

    resp = await client.get(f"/htmx/channel/{channel}", headers=HTMX)
    assert resp.status_code == 200
    assert f"/htmx/videos/{channel}" in resp.text
    assert f"/htmx/streams/{channel}" not in resp.text

    resp = await client.get(f"/htmx/videos/{channel}", headers=HTMX)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 10

    # Youtube serves the channel home for a missing tab: it must render as an empty tab
    resp = await client.get(f"/htmx/streams/{channel}", headers=HTMX)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) == 0
    assert soup.find("div", class_="yourss-empty") is not None

    resp = await client.get(f"/htmx/playlists/{channel}", headers=HTMX)
    assert resp.status_code == 422


async def test_api_resolve_from_video(client: AsyncClient) -> None:
    channel = "UCVooVnzQxPSTXTMzSi1s6uw"
    feed = await YoutubeApi().get_channel_rss(channel)
    video_id = feed.entries[0].to_video().video_id

    resp = await client.get("/api/resolve", params={"q": f"https://www.youtube.com/watch?v={video_id}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == channel


async def test_custom_pages_disabled(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(current_config, "custom_pages_enabled", False)

    # The home page and the multi channel pages are an error page
    for path in ("/", "/UCVooVnzQxPSTXTMzSi1s6uw"):
        resp = await client.get(path)
        assert resp.status_code == 403
        assert "Custom pages are disabled" in resp.text
        assert "data-page-names" not in resp.text
    resp = await client.get("/api/resolve", params={"q": "UCVooVnzQxPSTXTMzSi1s6uw"})
    assert resp.status_code == 403

    # User pages remain, without the way to a custom copy
    resp = await client.get("/u/demo")
    assert resp.status_code == 200
    assert "yourss-copy-page" not in resp.text


async def test_removed_routes(client: AsyncClient) -> None:
    # A channel is browsed inside a page, it has no page of its own; the proxy routes are gone
    for path in (
        "/c/UCVooVnzQxPSTXTMzSi1s6uw",
        "/channel/UCVooVnzQxPSTXTMzSi1s6uw",
        "/proxy/rss/UCVooVnzQxPSTXTMzSi1s6uw",
        "/proxy/avatar/@JonnyGiger",
    ):
        resp = await client.get(path)
        assert resp.status_code == 404


async def test_htmx_routes_only_answer_htmx(client: AsyncClient) -> None:
    # Without the header htmx sends, a fragment does not exist (crawlers, direct visits)
    resp = await client.get("/htmx/channel/UCVooVnzQxPSTXTMzSi1s6uw")
    assert resp.status_code == 404
    resp = await client.get("/htmx/rss/UCVooVnzQxPSTXTMzSi1s6uw", headers={"HX-Request": "false"})
    assert resp.status_code == 404


PLAYLIST_ID = "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"


@mark.parametrize("query", [PLAYLIST_ID, f"https://www.youtube.com/playlist?list={PLAYLIST_ID}&si=abc"])
async def test_api_resolve_playlist(client: AsyncClient, query: str) -> None:
    resp = await client.get("/api/resolve", params={"q": query})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["kind"] == "playlist" and payload["id"] == PLAYLIST_ID and payload["name"]

    resp = await client.get("/api/resolve", params={"q": "PL" + "A" * 32})
    assert resp.status_code == 404


async def test_page_lists_what_its_address_names(client: AsyncClient) -> None:
    # The owner of the playlist is not a subscription: only the playlist is listed, and can be removed
    resp = await client.get(f"/{PLAYLIST_ID}")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.find_all("li", class_="yourss-channel") == []
    removable = [str(button["data-id"]) for button in soup.find_all("button", attrs={"data-action": "remove-channel"})]
    assert removable == [PLAYLIST_ID]

    # With its channel next to it, each video is listed once
    resp = await client.get(f"/{PLAYLIST_ID},UCVooVnzQxPSTXTMzSi1s6uw")
    soup = BeautifulSoup(resp.text, features="html.parser")
    ids = [str(div["data-video-id"]) for div in soup.find_all("div", class_="yourss-video")]
    assert len(ids) == len(set(ids)) > 15
    assert len(soup.find_all("button", attrs={"data-action": "remove-channel"})) == 2


async def test_htmx_playlist(client: AsyncClient) -> None:
    resp = await client.get(f"/htmx/playlist/{PLAYLIST_ID}", headers=HTMX)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    # Youtube decides how many entries the feed of a playlist holds: only check there are some
    assert len(soup.find_all("div", class_="yourss-video")) > 0
    hero = soup.find("section", class_="yourss-hero")
    assert hero is not None and hero["data-channel-page"] == PLAYLIST_ID

    # The link to the channel of a video stays on the page the fragment is shown in
    headers = HTMX | {"HX-Current-URL": f"http://test/u/demo?p={PLAYLIST_ID}"}
    resp = await client.get(f"/htmx/playlist/{PLAYLIST_ID}", headers=headers)
    soup = BeautifulSoup(resp.text, features="html.parser")
    links = [str(a["href"]) for a in soup.find_all("a", class_="yourss-video-channel")]
    assert links and all(link.startswith("/u/demo?c=UC") for link in links)

    resp = await client.get("/htmx/playlist/UCVooVnzQxPSTXTMzSi1s6uw", headers=HTMX)
    assert resp.status_code == 422


async def test_handle_in_address_points_to_the_add_form(client: AsyncClient) -> None:
    resp = await client.get("/@JonnyGiger")
    assert resp.status_code == 404
    assert "use the form of the home page" in resp.text
    soup = BeautifulSoup(resp.text, features="html.parser")
    action = soup.find("a", class_="yourss-empty-action")
    assert action is not None and action["href"] == "/"
