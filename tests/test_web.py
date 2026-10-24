import re

from bs4 import BeautifulSoup
from httpx import AsyncClient, BasicAuth
from pytest import MonkeyPatch, mark

from yourss.settings import current_config, static_folder
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
    themes = soup.select('.yourss-home-themes [data-action="set-theme"]')
    assert [str(el["data-value"]) for el in themes] == ["neon", "dark", "light"]
    # The demo page is a plain subscription list
    demo = soup.find("a", id="yourss-demo")
    assert demo is not None
    resp = await client.get(str(demo["href"]))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None and len(str(soup.body["data-page-names"]).split(",")) == 4


async def test_page_is_editable(client: AsyncClient) -> None:
    # Duplicates are dropped and the order is kept
    resp = await client.get("/UCVooVnzQxPSTXTMzSi1s6uw,UCQsmxaMzYr76Yd1iqMEq8TA,UCVooVnzQxPSTXTMzSi1s6uw")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert soup.body is not None
    assert soup.body["data-page-names"] == "UCVooVnzQxPSTXTMzSi1s6uw,UCQsmxaMzYr76Yd1iqMEq8TA"
    assert len(soup.find_all("button", attrs={"data-action": "remove-channel"})) == 2


async def test_page_is_read_only(client: AsyncClient) -> None:
    resp = await client.get("/p/fun")
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
    # Bob's password is foo, it protects the user and its folders
    for path in ("/u/bob", "/u/bob/podcast"):
        resp = await client.get(path)
        assert resp.status_code == 401
        resp = await client.get(path, auth=BasicAuth("bob", "password"))
        assert resp.status_code == 401
        resp = await client.get(path, auth=BasicAuth("bob", "foo"))
        assert resp.status_code == 200

    # The user is the identity: the name typed in the browser prompt is not checked, only the password
    resp = await client.get("/u/bob", auth=BasicAuth("anyone", "foo"))
    assert resp.status_code == 200

    # Alice has no password
    resp = await client.get("/u/alice")
    assert resp.status_code == 200

    # Unknown user, unknown page, and the addresses of 0.82
    for path in ("/u/unknown", "/p/unknown", "/user/bob", "/htmx/folder/alice/fun"):
        resp = await client.get(path, headers=HTMX)
        assert resp.status_code == 404
    # An unknown user is a page, not a JSON detail
    for path in ("/u/unknown", "/u/unknown/fun"):
        resp = await client.get(path)
        assert resp.status_code == 404 and resp.headers["content-type"].startswith("text/html")
        assert "This user does not exist" in resp.text

    # A hidden page has no address of its own, it is read inside a user
    resp = await client.get("/p/cards")
    assert resp.status_code == 404
    resp = await client.get("/u/alice/cards")
    assert resp.status_code == 200


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

    # Well formed but unknown ids stay in the sidebar, marked, and the page tells it in one line
    resp = await client.get("/" + ",".join(names[:-1]))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, features="html.parser")
    assert len(soup.find_all("div", id=re.compile(r"^yourss-video-"))) > 30
    assert soup.find("div", class_="yourss-error") is None
    failed = soup.find_all("li", class_="is-failed")
    # Unnamed entries are listed last, by raw id
    assert [str(li.get("data-channel-id") or li.get("data-playlist-id")) for li in failed] == sorted(names[3:5])
    assert all(li.find("span", class_="is-failed") is not None for li in failed)
    (notice,) = soup.find_all("div", class_="is-warning")
    assert "2 of 5 subscriptions could not be refreshed." in notice.get_text()
    assert len(notice.find_all("li")) == 2
    # A click on a failed entry is a retry: it aborts the request in flight and shows the failure state on error
    assert all(a["hx-sync"] == "#yourss-content:replace" for li in failed for a in li.find_all("a"))
    assert soup.find("template", id="yourss-failed-template") is not None


@mark.parametrize("path", ["/foo", "/favicon.ico", "/robots.txt", "/foo,UCVooVnzQxPSTXTMzSi1s6uw"])
async def test_stray_path_is_not_a_page(client: AsyncClient, path: str) -> None:
    resp = await client.get(path)
    assert resp.status_code == 404


FOLDERS = ["fun", "cards", "podcast", "music"]


async def test_user_without_folder(client: AsyncClient) -> None:
    resp = await client.get("/u/alice")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")
    assert [str(folder["data-folder"]) for folder in soup.select("details.yourss-folder")] == FOLDERS
    # The row shows the label of the user, its address is the page
    assert [row.get_text(strip=True) for row in soup.select("details.yourss-folder > summary .yourss-label")] == [
        "fun",
        "Card magic",
        "podcast",
        "music",
    ]
    # Every folder is closed and empty, the script picks the one to open: nothing was asked to Youtube
    assert soup.select("details.yourss-folder[open]") == []
    assert soup.select("details.yourss-folder li") == []
    assert soup.select("#yourss-content .yourss-video") == []
    (row,) = soup.select("details[data-folder=cards] > summary")
    assert row["hx-get"] == "/u/alice/cards" and row["hx-push-url"] == "/u/alice/cards"
    # A user offers no flat copy
    assert soup.select("a.yourss-copy-page") == []


async def test_user_folder(client: AsyncClient) -> None:
    resp = await client.get("/u/alice/fun")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")
    (title,) = soup.select("title")
    assert title.get_text() == "YouRSS - u/alice/fun"
    # The folder of the address is open with its entries, its Home is the content
    assert [str(folder["data-folder"]) for folder in soup.select("details.yourss-folder[open]")] == ["fun"]
    links = [str(a["hx-push-url"]) for a in soup.select("ul[data-folder-list=fun] a")]
    assert len(links) == 4
    assert all(link.startswith("/u/alice/fun?c=UC") or link.startswith("/u/alice/fun?p=PL") for link in links)
    assert soup.select("ul[data-folder-list=cards] li") == []
    assert soup.select("#yourss-content [data-folder-page=fun] .yourss-video")
    # The channel link of a card keeps the folder
    cards = {str(a["hx-push-url"]) for a in soup.select(".yourss-video a.yourss-video-channel")}
    assert cards and all(link.startswith("/u/alice/fun?c=UC") for link in cards)

    # A hidden page, under the label of the user
    resp = await client.get("/u/alice/cards")
    (title,) = BeautifulSoup(resp.text, "html.parser").select("title")
    assert title.get_text() == "YouRSS - u/alice/cards"

    for unknown in ("unknown", "a" * 33, "podcast/more"):
        resp = await client.get(f"/u/alice/{unknown}")
        assert resp.status_code == 404
        assert unknown not in resp.text
    # A page the user does not hold
    resp = await client.get("/u/bob/cards", auth=BasicAuth("bob", "foo"))
    assert resp.status_code == 404


async def test_user_folder_fragment(client: AsyncClient) -> None:
    # Same address, the header of htmx: the fragment. Its links name its folder, not the page the visitor comes from
    resp = await client.get("/u/alice/fun", headers=HTMX | {"HX-Current-URL": "http://test/u/alice/podcast"})
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")
    assert soup.select("html") == []
    (title,) = soup.select("title")
    assert title.get_text() == "YouRSS - u/alice/fun"
    assert soup.select("[data-folder-page=fun] div.yourss-video")
    cards = {str(a["hx-push-url"]) for a in soup.select(".yourss-video a.yourss-video-channel")}
    assert cards and all(link.startswith("/u/alice/fun?c=UC") for link in cards)
    (entries,) = soup.select("ul#yourss-folder-list-fun")
    assert entries["hx-swap-oob"] == "true"
    links = [str(a["hx-push-url"]) for a in entries.select("a")]
    assert len(links) == 4
    assert all(link.startswith("/u/alice/fun?c=UC") or link.startswith("/u/alice/fun?p=PL") for link in links)
    (status,) = soup.select("div#yourss-fetch-status")
    assert status["hx-swap-oob"] == "true"


@mark.parametrize(
    "path, http_status",
    [
        ("/u/alice/unknown", 404),
        ("/u/bob/cards", 401),  # bob is protected: the password first
        ("/u/unknown/fun", 404),
        ("/u/bob/podcast", 401),  # the password of the user protects its fragments, before any 404
    ],
)
async def test_user_folder_fragment_refused(client: AsyncClient, path: str, http_status: int) -> None:
    resp = await client.get(path, headers=HTMX)
    assert resp.status_code == http_status


@mark.parametrize("path", ["/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"])
async def test_apple_touch_icon_at_the_root(client: AsyncClient, path: str) -> None:
    # iOS probes these addresses when it cannot read the page, and the page links the icon without a version
    resp = await client.get(path)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "public, max-age=3600"
    assert resp.content == (static_folder / "icons" / "apple-touch-icon.png").read_bytes()
    page = await client.get("/")
    assert '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />' in page.text


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
    resp = await client.get("/p/fun")
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
    resp = await client.get("/p/fun")
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
    headers = HTMX | {"HX-Current-URL": f"http://test/u/bob?p={PLAYLIST_ID}"}
    resp = await client.get(f"/htmx/playlist/{PLAYLIST_ID}", headers=headers)
    soup = BeautifulSoup(resp.text, features="html.parser")
    links = [str(a["href"]) for a in soup.find_all("a", class_="yourss-video-channel")]
    assert links and all(link.startswith("/u/bob?c=UC") for link in links)

    resp = await client.get("/htmx/playlist/UCVooVnzQxPSTXTMzSi1s6uw", headers=HTMX)
    assert resp.status_code == 422


async def test_handle_in_address_points_to_the_add_form(client: AsyncClient) -> None:
    resp = await client.get("/@JonnyGiger")
    assert resp.status_code == 404
    assert "use the form of the home page" in resp.text
    soup = BeautifulSoup(resp.text, features="html.parser")
    action = soup.find("a", class_="yourss-empty-action")
    assert action is not None and action["href"] == "/"


async def test_avatar_redirects_to_youtube(client: AsyncClient) -> None:
    resp = await client.get(f"/avatar/{CHANNEL}")
    assert resp.status_code == 307
    assert "googleusercontent.com" in resp.headers["Location"]
    assert resp.headers["Cache-Control"] == "public, max-age=86400"


async def test_avatar_falls_back_on_the_initial(client: AsyncClient) -> None:
    resp = await client.get("/avatar/UCAAAAAAAAAAAAAAAAAAAAAA", params={"n": "j"})
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("image/svg+xml")
    assert resp.headers["Cache-Control"] == "public, max-age=3600"
    assert ">J</text>" in resp.text

    resp = await client.get("/avatar/UCAAAAAAAAAAAAAAAAAAAAAA", params={"n": "<b>"})
    assert resp.status_code == 422
    resp = await client.get("/avatar/foo")
    assert resp.status_code == 422


async def test_pages_are_compressed_on_request(client: AsyncClient) -> None:
    resp = await client.get("/u/alice/fun", headers={"Accept-Encoding": "gzip", "HX-Request": "true"})
    assert resp.status_code == 200 and resp.headers["content-encoding"] == "gzip"
    assert int(resp.headers["content-length"]) < len(resp.content) / 5  # the body is decompressed by the client
    plain = await client.get("/u/alice/fun", headers={"Accept-Encoding": "identity"})
    assert plain.status_code == 200 and "content-encoding" not in plain.headers
