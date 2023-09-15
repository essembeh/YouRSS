from yourss.model import RssFeed
from yourss.youtube import (
    YoutubeScrapper,
    youtube_get_rss_feed,
    yt_home_url,
    yt_html_get,
    yt_rss_url,
)

USER = "DAN1ELmadison"
USER_HOME = yt_home_url(user=USER)
USER_RSS = yt_rss_url(user=USER)

CHANNEL_ID = "UCa_Dlwrwv3ktrhCy91HpVRw"
CHANNEL_ID_HOME = yt_home_url(channel_id=CHANNEL_ID)
CHANNEL_ID_RSS = yt_rss_url(channel_id=CHANNEL_ID)

SLUG = "@LostAngelus52"
SLUG_HOME = yt_home_url(slug=SLUG)


def test_channel_rssfeed():
    feed = RssFeed.fromresponse(youtube_get_rss_feed(CHANNEL_ID))
    assert feed is not None
    assert feed.title == "Jeremy Griffith"


def test_channel_metadata():
    response = yt_html_get(CHANNEL_ID_HOME)
    metadata = YoutubeScrapper.fromresponse(response)
    assert metadata.title == "Jeremy Griffith"
    assert (
        metadata.homepage_url
        == "https://www.youtube.com/channel/UCa_Dlwrwv3ktrhCy91HpVRw"
    )
    assert metadata.avatar_url is not None


def test_user_rssfeed():
    feed = RssFeed.fromresponse(youtube_get_rss_feed(USER))
    assert feed is not None
    assert feed.title == "Daniel Madison"


def test_user_metadata():
    response = yt_html_get(USER_HOME)
    metadata = YoutubeScrapper.fromresponse(response)
    assert metadata.title == "Daniel Madison"
    assert (
        metadata.homepage_url
        == "https://www.youtube.com/channel/UCB99aK4f2WaH96joccxLvSQ"
    )
    assert metadata.avatar_url is not None


def test_slug_metadata():
    response = yt_html_get(SLUG_HOME)
    metadata = YoutubeScrapper.fromresponse(response)
    assert metadata.title == "Jeremy Griffith"
    assert (
        metadata.homepage_url
        == "https://www.youtube.com/channel/UCa_Dlwrwv3ktrhCy91HpVRw"
    )
    assert metadata.avatar_url is not None
