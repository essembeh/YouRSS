"""
A fake Youtube for the tests (docs/specs/youtube-fake.md): an httpx transport which answers from
files recorded under `tests/data/youtube/`, or records them from the real Youtube.
"""

import gzip
import hashlib
import re
from enum import StrEnum
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from httpx import AsyncBaseTransport, AsyncClient, Request, Response

FIXTURES = Path(__file__).parent / "data" / "youtube"
CONTENT_TYPES = {".xml": "application/xml", ".json": "application/json", ".html": "text/html; charset=utf-8"}
_STATUS_SUFFIX = re.compile(r"^\.\d{3}$")


class Mode(StrEnum):
    REPLAY = "replay"
    RECORD = "record"
    LIVE = "live"


class FixtureError(Exception):
    pass


def fixture_path(request: Request) -> Path:
    """The file holding the answer of a request (spec §3), relative to `FIXTURES`."""
    url = request.url
    query = parse_qs(url.query.decode())
    if url.path == "/feeds/videos.xml":
        (key,) = query.get("channel_id") or query.get("playlist_id") or [""]
        if key:
            return FIXTURES / "feeds" / f"{key}.xml"
    elif url.path == "/oembed":
        video = parse_qs(urlparse(query.get("url", [""])[0]).query).get("v", [""])[0]
        if video:
            return FIXTURES / "oembed" / f"{video}.json"
    elif url.path == "/playlist":
        (playlist,) = query.get("list") or [""]
        if re.fullmatch(r"[A-Za-z0-9_-]+", playlist):
            return FIXTURES / "pages" / f"playlist.{playlist}.html.gz"
    elif url.path == "/youtubei/v1/browse" and request.method == "POST":
        return FIXTURES / "browse" / f"{hashlib.sha256(request.content).hexdigest()[:16]}.json.gz"
    else:
        parts = url.path.strip("/").split("/")
        if parts[0].startswith("@"):
            name, tabs = parts[0][1:].lower(), parts[1:]
        elif parts[0] == "channel" and len(parts) > 1:
            name, tabs = parts[1], parts[2:]
        else:
            name, tabs = "", []
        if (
            re.fullmatch(r"[A-Za-z0-9_.-]+", name)
            and all(re.fullmatch(r"[a-z]+", tab) for tab in tabs[:1])
            and len(tabs) <= 1
        ):
            return FIXTURES / "pages" / ".".join([name, *tabs, "html.gz"])
    raise FixtureError(f"No fixture for {request.method} {url}")


def _recorded(path: Path) -> tuple[int, Path] | None:
    """The status and file of a recorded answer: the file itself (200) or its `<file>.<status>` twin."""
    if path.is_file():
        return 200, path
    for twin in sorted(path.parent.glob(f"{path.name}.*")):
        if _STATUS_SUFFIX.match(twin.suffix):
            return int(twin.suffix[1:]), twin
    return None


def _read(path: Path) -> bytes:
    content = path.read_bytes()
    return gzip.decompress(content) if path.name.endswith(".gz") else content


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(content, mtime=0) if path.name.endswith(".gz") else content)


def _content_type(path: Path) -> str:
    name = path.name.removesuffix(".gz")
    return CONTENT_TYPES.get(Path(name).suffix, "application/octet-stream")


class FakeYoutube(AsyncBaseTransport):
    """Replay: answer from the fixture of the request. Record: ask Youtube and keep the answer (spec §2)."""

    def __init__(self, mode: Mode) -> None:
        self.mode = mode
        self.served: set[Path] = set()

    async def handle_async_request(self, request: Request) -> Response:
        path = fixture_path(request)
        recorded = _recorded(path)
        if self.mode == Mode.RECORD and (recorded is None or recorded[0] != 200):
            recorded = await self._record(request, path)
        if recorded is None:
            raise FixtureError(
                f"Missing fixture {path.relative_to(FIXTURES)}: run YOURSS_TEST_YOUTUBE=record just test"
            )
        status, file = recorded
        self.served.add(file)
        content = _read(file) if status == 200 else b""
        return Response(status, content=content, headers={"content-type": _content_type(path)}, request=request)

    async def _record(self, request: Request, path: Path) -> tuple[int, Path]:
        # Redirects are followed here, so that a fixture is always the final answer
        async with AsyncClient(follow_redirects=True) as client:
            answer = await client.request(request.method, request.url, headers=request.headers, content=request.content)
        if answer.status_code == 200:
            _write(path, answer.content)
            for twin in path.parent.glob(f"{path.name}.*"):
                if _STATUS_SUFFIX.match(twin.suffix):
                    twin.unlink()
            return 200, path
        # A failure is kept only when no good answer was recorded before (a 404 window of Youtube)
        twin = path.with_name(f"{path.name}.{answer.status_code}")
        _write(twin, b"")
        return answer.status_code, twin
