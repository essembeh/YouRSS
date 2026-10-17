import os
import shutil
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from httpx import ASGITransport, AsyncClient
from pytest import Config, Item, MonkeyPatch, fixture, mark

from tests.youtube_fake import FakeYoutube, Mode
from yourss.main import app
from yourss.settings import current_config
from yourss.youtube import YoutubeApi

# How the tests reach Youtube (docs/specs/youtube-fake.md §2): recorded answers unless told otherwise
YOUTUBE_MODE = Mode(os.environ.get("YOURSS_TEST_YOUTUBE", Mode.REPLAY))


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "live: needs the real Youtube, skipped unless YOURSS_TEST_YOUTUBE=live")


def pytest_collection_modifyitems(items: list[Item]) -> None:
    if YOUTUBE_MODE != Mode.LIVE:
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(mark.skip(reason="needs the real Youtube (YOURSS_TEST_YOUTUBE=live)"))


@fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as client:
        yield client


@fixture(autouse=True, scope="session")
def test_cache_folder() -> Iterator[Path]:
    """The suite caches in its own temporary folder, never in the one of the development server."""
    folder = Path(mkdtemp(prefix="yourss-test-"))
    with MonkeyPatch.context() as patch:
        patch.setattr(current_config, "cache_enabled", True)
        patch.setattr(current_config, "cache_folder", folder)
        yield folder
    shutil.rmtree(folder, ignore_errors=True)


@fixture(autouse=True, scope="session")
def fake_youtube() -> Iterator[FakeYoutube | None]:
    """Every `YoutubeApi()` of the suite talks to the fake transport, except in live mode."""
    if YOUTUBE_MODE == Mode.LIVE:
        yield None
        return
    fake = FakeYoutube(YOUTUBE_MODE)
    original = YoutubeApi.__init__

    def with_fake(self: YoutubeApi, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("async_client_factory", lambda **options: AsyncClient(transport=fake, **options))
        original(self, *args, **kwargs)

    with MonkeyPatch.context() as patch:
        patch.setattr(YoutubeApi, "__init__", with_fake)
        yield fake
