from pathlib import Path

from httpx import Request
from pytest import MonkeyPatch, mark, raises

from tests import youtube_fake
from tests.youtube_fake import FakeYoutube, FixtureError, Mode, fixture_path

BASE = "https://www.youtube.com"


@mark.parametrize(
    ("method", "url", "expected"),
    [
        ("GET", f"{BASE}/feeds/videos.xml?channel_id=UCVooVnzQxPSTXTMzSi1s6uw", "feeds/UCVooVnzQxPSTXTMzSi1s6uw.xml"),
        (
            "GET",
            f"{BASE}/feeds/videos.xml?playlist_id=PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk",
            "feeds/PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk.xml",
        ),
        (
            "GET",
            f"{BASE}/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dq5IMA244HXw",
            "oembed/q5IMA244HXw.json",
        ),
        ("GET", f"{BASE}/@JonnyGiger?ucbcb=1", "pages/jonnygiger.html.gz"),
        ("GET", f"{BASE}/@jonnygiger/videos?ucbcb=1", "pages/jonnygiger.videos.html.gz"),
        ("GET", f"{BASE}/channel/UCVooVnzQxPSTXTMzSi1s6uw/shorts", "pages/UCVooVnzQxPSTXTMzSi1s6uw.shorts.html.gz"),
        (
            "GET",
            f"{BASE}/playlist?list=PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk&ucbcb=1",
            "pages/playlist.PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk.html.gz",
        ),
    ],
)
def test_fixture_path(method: str, url: str, expected: str) -> None:
    assert fixture_path(Request(method, url)) == youtube_fake.FIXTURES / expected


def test_fixture_path_browse_depends_on_the_body() -> None:
    first = fixture_path(Request("POST", f"{BASE}/youtubei/v1/browse", content=b'{"continuation": "a"}'))
    second = fixture_path(Request("POST", f"{BASE}/youtubei/v1/browse", content=b'{"continuation": "b"}'))
    assert first.parent.name == "browse" and first.name.endswith(".json.gz") and first != second


@mark.parametrize(
    "url", [f"{BASE}/", f"{BASE}/feeds/videos.xml", f"{BASE}/watch?v=x", f"{BASE}/@a/b/c", f"{BASE}/@a%20b"]
)
def test_fixture_path_unknown(url: str) -> None:
    with raises(FixtureError):
        fixture_path(Request("GET", url))


async def test_replay_and_record(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(youtube_fake, "FIXTURES", tmp_path)
    request = Request("GET", f"{BASE}/feeds/videos.xml?channel_id=UCVooVnzQxPSTXTMzSi1s6uw")
    fake = FakeYoutube(Mode.REPLAY)
    with raises(FixtureError, match=r"Missing fixture feeds/UCVooVnzQxPSTXTMzSi1s6uw\.xml"):
        await fake.handle_async_request(request)

    (tmp_path / "feeds").mkdir()
    (tmp_path / "feeds" / "UCVooVnzQxPSTXTMzSi1s6uw.xml").write_bytes(b"<feed/>")
    resp = await fake.handle_async_request(request)
    assert resp.status_code == 200 and resp.content == b"<feed/>" and resp.headers["content-type"] == "application/xml"

    # A recorded failure answers its status with no body
    (tmp_path / "feeds" / "UCAAAAAAAAAAAAAAAAAAAAAA.xml.404").write_bytes(b"")
    resp = await fake.handle_async_request(
        Request("GET", f"{BASE}/feeds/videos.xml?channel_id=UCAAAAAAAAAAAAAAAAAAAAAA")
    )
    assert resp.status_code == 404 and resp.content == b""


async def test_gzip_fixture(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(youtube_fake, "FIXTURES", tmp_path)
    path = tmp_path / "pages" / "jonnygiger.html.gz"
    youtube_fake._write(path, b"<html>hello</html>")
    assert path.read_bytes()[:2] == b"\x1f\x8b"
    resp = await FakeYoutube(Mode.REPLAY).handle_async_request(Request("GET", f"{BASE}/@JonnyGiger"))
    assert resp.text == "<html>hello</html>" and resp.headers["content-type"].startswith("text/html")
