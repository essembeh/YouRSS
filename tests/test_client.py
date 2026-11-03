from httpx import MockTransport, Request, Response

from tests.youtube_fake import FakeYoutube
from yourss.youtube import YoutubeApi, shared_client

CHANNEL = "UCVooVnzQxPSTXTMzSi1s6uw"


async def test_shared_client(fake_youtube: FakeYoutube | None) -> None:
    assert YoutubeApi()._async_client is None
    async with shared_client(transport=fake_youtube) as client:
        api = YoutubeApi()
        assert api._async_client is client
        feed = await api.get_channel_rss(CHANNEL, refresh=True)
        assert feed.channel_id == CHANNEL
        opened = not client.is_closed
    assert opened
    assert client.is_closed
    assert YoutubeApi()._async_client is None


async def test_shared_client_keeps_no_cookie() -> None:
    sent: list[str | None] = []

    def answer(request: Request) -> Response:
        sent.append(request.headers.get("cookie"))
        return Response(200, headers={"set-cookie": "YSC=visitor; Domain=.youtube.com; Path=/"}, text="ok")

    async with shared_client(transport=MockTransport(answer)) as client:
        await client.get("/a")
        await client.get("/b")
    assert sent == ["CONSENT=YES+cb", "CONSENT=YES+cb"]
