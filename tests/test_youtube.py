from yourss.model import RssFeed
from yourss.youtube import (
    YoutubeScrapper,
    YoutubeUrl,
    youtube_get_metadata,
    youtube_get_rss_feed,
    yt_html_get,
)

USER = "DAN1ELmadison"
USER_HOME = YoutubeUrl.user_home(USER)
USER_RSS = YoutubeUrl.user_rss(USER)

CHANNEL_ID = "UCa_Dlwrwv3ktrhCy91HpVRw"
CHANNEL_ID_HOME = YoutubeUrl.channel_home(CHANNEL_ID)
CHANNEL_ID_RSS = YoutubeUrl.channel_rss(CHANNEL_ID)

SLUG = "@LostAngelus52"
SLUG_HOME = YoutubeUrl.slug_home(SLUG)


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


def test_avatar():
    metadata = youtube_get_metadata("@jonnygiger")
    assert metadata is not None
    print(">>>>>>>>>>>>>>", metadata.avatar_url)
    assert metadata.avatar_url is not None
