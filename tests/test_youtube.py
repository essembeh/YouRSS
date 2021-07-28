from re import fullmatch
from yourss.youtube import (
    YOUTUBE_URL_PATTERN,
    youtube_find_channel_infos,
    yt_scrap_metadata,
    yt_get_page,
    yt_feed_url,
)


def test_url():
    assert (
        fullmatch(YOUTUBE_URL_PATTERN, "https://www.youtube.com/user/DAN1ELmadison")
        is not None
    )
    assert (
        fullmatch(
            YOUTUBE_URL_PATTERN,
            "https://www.youtube.com/channel/UCa_Dlwrwv3ktrhCy91HpVRw",
        )
        is not None
    )
    assert (
        fullmatch(
            YOUTUBE_URL_PATTERN,
            "https://www.youtube.com/results?search_query=jonny+giger",
        )
        is None
    )


def test_scrap():
    channel_id = "UCa_Dlwrwv3ktrhCy91HpVRw"
    url = f"https://www.youtube.com/channel/{channel_id}"

    content = yt_get_page(url)
    assert content
    metadata = yt_scrap_metadata(content)
    assert metadata
    assert metadata["og:title"] == "Jeremy Griffith"
    assert "og:image" in metadata
    assert "og:url" in metadata


def test_metadata():
    channel_id = "UCa_Dlwrwv3ktrhCy91HpVRw"
    url = f"https://www.youtube.com/channel/{channel_id}"

    infos = youtube_find_channel_infos(url)
    infos2 = youtube_find_channel_infos(channel_id)
    assert infos == infos2
    assert infos["id"] == channel_id
    assert infos["name"] == "Jeremy Griffith"
    assert infos["rss_url"] == yt_feed_url(channel_id)
