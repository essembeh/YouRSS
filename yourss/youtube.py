from re import fullmatch
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests import get, post

from .rss import RssFeed

YOUTUBE_URL_PATTERN = "https://www\\.youtube\\.com/(channel|user|c)/(?P<name>[^/]+)"
OG_URL = "og:url"
OG_IMAGE = "og:image"
OG_TITLE = "og:title"


def yt_feed_url(yt_identifier: str):
    if len(yt_identifier) == 24:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={yt_identifier}"
    return f"https://www.youtube.com/feeds/videos.xml?user={yt_identifier}"


def yt_scrap_metadata(page_content: str):
    soup = BeautifulSoup(page_content, features="lxml")
    return {
        meta["property"]: meta.get("content")
        for meta in soup.find_all("meta")
        if "property" in meta.attrs
        if "property" in meta.attrs
    }


def yt_get_page(youtube_url: str):
    """
    get a youtube page content with cookie accept if needed
    """
    assert fullmatch(YOUTUBE_URL_PATTERN, youtube_url)
    response = get(youtube_url, timeout=5)
    assert response.ok
    soup = BeautifulSoup((get(youtube_url).text), features="lxml")
    for form in soup.find_all("form", attrs={"method": "POST"}):
        response = post(
            (form.attrs["action"]),
            data={
                element.attrs["name"]: element.attrs["value"]
                for element in form.find_all("input")
                if "name" in element.attrs and "value" in element.attrs
            },
            timeout=5,
        )
        assert response.ok
        break

    return response.text


def youtube_find_channel_infos(value: str):
    identifier = None
    rssfeed = None
    metadata = None
    if value.startswith("http"):
        metadata = yt_scrap_metadata(yt_get_page(value))
        assert OG_URL in metadata
        og_url = urlparse(metadata[OG_URL])
        identifier = og_url.path.split("/")[(-1)]
        rssfeed = RssFeed.fromurl(yt_feed_url(identifier))
        if not rssfeed:
            raise AssertionError
    else:
        rssfeed = RssFeed.fromurl(yt_feed_url(value))
        assert rssfeed
        identifier = rssfeed.channel_id
        metadata = yt_scrap_metadata(yt_get_page(rssfeed.link))
        assert OG_URL in metadata
    if identifier:
        if not (rssfeed and metadata):
            raise AssertionError
        return {
            "id": identifier,
            "name": metadata[OG_TITLE],
            "rss_url": rssfeed.url,
            "avatar": metadata[OG_IMAGE],
        }


# okay decompiling __pycache__/youtube.cpython-37.pyc
