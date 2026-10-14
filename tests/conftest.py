import shutil
from collections.abc import AsyncIterator, Iterator

from httpx import ASGITransport, AsyncClient
from pytest import fixture

from yourss.main import app
from yourss.settings import current_config


@fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as client:
        yield client


@fixture(autouse=True, scope="session")
def drop_temporary_cache() -> Iterator[None]:
    """The default settings create a temporary cache folder when the application is imported: clean it up."""
    yield
    folder = current_config.cache_folder
    if folder is not None and folder.name.startswith("yourss-"):
        shutil.rmtree(folder, ignore_errors=True)
