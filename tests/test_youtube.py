import pytest

from yourss.youtube import YoutubeScrapper, YoutubeUrl

USER = "DAN1ELmadison"
USER_HOME = YoutubeUrl.user_home(USER)
USER_RSS = YoutubeUrl.user_rss(USER)

CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"
CHANNEL_ID_HOME = YoutubeUrl.channel_home(CHANNEL_ID)
CHANNEL_ID_RSS = YoutubeUrl.channel_rss(CHANNEL_ID)

SLUG = "@jonnygiger"
SLUG_HOME = YoutubeUrl.slug_home(SLUG)


@pytest.mark.asyncio
async def test_channel_rssfeed(yt_client):
    feed = await yt_client.get_rss_feed(CHANNEL_ID)
    assert feed.title == "Jonny Giger"


@pytest.mark.asyncio
async def test_channel_metadata(yt_client):
    response = await yt_client.get_html(CHANNEL_ID_HOME)
    metadata = YoutubeScrapper.fromresponse(response)
    assert metadata.title == "Jonny Giger"
    assert (
        metadata.homepage_url
        == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    )
    assert metadata.avatar_url is not None


@pytest.mark.asyncio
async def test_user_rssfeed(yt_client):
    feed = await yt_client.get_rss_feed(USER)
    assert feed.title == "Daniel Madison"


@pytest.mark.asyncio
async def test_user_metadata(yt_client):
    response = await yt_client.get_html(USER_HOME)
    metadata = YoutubeScrapper.fromresponse(response)
    assert metadata.title == "Daniel Madison"
    assert (
        metadata.homepage_url
        == "https://www.youtube.com/channel/UCB99aK4f2WaH96joccxLvSQ"
    )
    assert metadata.avatar_url is not None


@pytest.mark.asyncio
async def test_slug_metadata(yt_client):
    response = await yt_client.get_html(SLUG_HOME)
    metadata = YoutubeScrapper.fromresponse(response)
    assert metadata.title == "Jonny Giger"
    assert (
        metadata.homepage_url
        == "https://www.youtube.com/channel/UCVooVnzQxPSTXTMzSi1s6uw"
    )
    assert metadata.avatar_url is not None


@pytest.mark.asyncio
async def test_avatar(yt_client):
    metadata = await yt_client.get_metadata("@jonnygiger")
    assert metadata is not None
    assert metadata.avatar_url is not None
