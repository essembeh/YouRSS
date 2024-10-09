import re
from typing import Dict

from bs4 import BeautifulSoup, ResultSet

ALLOWED_HOSTS = ["consent.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"]

MOZILLA_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
)

CHANNEL_PATTERN = r"^UC[\w-]{22}$"
PLAYLIST_PATTERN = r"^PL[\w-]{32}$"
USER_PATTERN = r"^@[\w-]+$"


def is_channel_id(text: str) -> bool:
    """
    Check if a string is a valid Youtube channel id
    """
    return bool(re.fullmatch(CHANNEL_PATTERN, text, flags=re.IGNORECASE))


def is_playlist_id(text: str) -> bool:
    """
    Check if a string is a valid Youtube playlist id
    """
    return bool(re.fullmatch(PLAYLIST_PATTERN, text, flags=re.IGNORECASE))


def is_user(text: str) -> bool:
    """
    Check if a string is a valid Youtube user
    """
    return bool(re.fullmatch(USER_PATTERN, text, flags=re.IGNORECASE))


def bs_parse(html_text: str) -> BeautifulSoup:
    """
    Parses the given HTML text and returns a BeautifulSoup object.
    """
    return BeautifulSoup(html_text, features="html.parser")


def html_get_rgpd_forms(html_text: str) -> ResultSet:
    """
    Extract RGPD forms from a Youtube page
    """
    return bs_parse(html_text).find_all(
        "form", attrs={"method": "POST", "action": "https://consent.youtube.com/save"}
    )


def html_get_metadata(html_text: str) -> Dict[str, str]:
    """
    Find all meta properties from given html page
    """
    soup = bs_parse(html_text)
    return {
        m["property"]: m.get("content")
        for m in soup.find_all("meta")
        if "property" in m.attrs
    }
