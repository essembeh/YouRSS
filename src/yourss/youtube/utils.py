import re
from urllib.parse import unquote

# Ids are ASCII only; `\w` would also accept the letters of every alphabet
CHANNEL_PATTERN = r"^UC[A-Za-z0-9_-]{22}$"
PLAYLIST_PATTERN = r"^PL[A-Za-z0-9_-]{32}$"
# A handle holds 3 to 30 letters (of any alphabet), digits, "_", "-" and "."
USER_PATTERN = r"^@[\w.-]{3,30}$"
# Address of a channel as copied from a browser: youtube.com/@name or youtube.com/channel/UC…
_CHANNEL_URL = re.compile(
    r"^(?:https?://)?(?:www\.|m\.)?youtube\.com/(?:channel/)?(@[\w.-]+|UC[\w-]{22})(?:[/?#].*)?$", re.IGNORECASE
)


def is_channel_id(text: str) -> bool:
    """
    Check if a string is a valid Youtube channel id
    """
    return bool(re.fullmatch(CHANNEL_PATTERN, text))


def is_playlist_id(text: str) -> bool:
    """
    Check if a string is a valid Youtube playlist id
    """
    return bool(re.fullmatch(PLAYLIST_PATTERN, text))


def is_user(text: str) -> bool:
    """
    Check if a string is a valid Youtube user
    """
    return bool(re.fullmatch(USER_PATTERN, text, flags=re.IGNORECASE))


# Address of a video: watch?v=…, youtu.be/…, shorts/…, live/… or embed/…
_VIDEO_URL = re.compile(
    r"^(?:https?://)?(?:(?:www\.|m\.|music\.)?youtube\.com/(?:watch\?(?:[^#]*&)?v=|shorts/|live/|embed/)|youtu\.be/)"
    r"([\w-]{11})(?:[?&/#].*)?$",
    re.IGNORECASE,
)


def parse_channel_reference(text: str) -> str | None:
    """The handle or the channel id named by what a visitor typed, ``None`` when it is neither."""
    # A handle with non ASCII letters is percent encoded in an address
    text = unquote(text.strip())
    if (match := _CHANNEL_URL.match(text)) is not None:
        text = match.group(1)
    return text if is_channel_id(text) or is_user(text) else None


def parse_video_reference(text: str) -> str | None:
    """The id of the video named by an address typed by a visitor, ``None`` when it is not one."""
    match = _VIDEO_URL.match(text.strip())
    return match.group(1) if match is not None else None
