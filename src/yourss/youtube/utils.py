import re

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
