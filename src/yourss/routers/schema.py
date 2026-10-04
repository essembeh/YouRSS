from typing import Annotated, Any

from fastapi import Path
from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints, TypeAdapter
from pydantic_core import PydanticCustomError

from ..settings import current_config
from ..youtube.utils import CHANNEL_PATTERN, PLAYLIST_PATTERN, USER_PATTERN
from .utils import split_subscriptions

UserId = Annotated[str, Path(pattern=USER_PATTERN)]
ChannelId = Annotated[str, Path(pattern=CHANNEL_PATTERN)]
PlaylistId = Annotated[str, Path(pattern=PLAYLIST_PATTERN)]

# One subscription of a custom page: a channel id or a playlist id. A handle is resolved once, by
# /api/resolve, when the channel is added: it is not accepted in an address (docs/specs/custom-pages.md §3)
Subscription = Annotated[str, StringConstraints(pattern=f"{CHANNEL_PATTERN}|{PLAYLIST_PATTERN}")]
# The same rule for the whole path, as a single expression: shown by the generated API documentation
_ONE = "|".join(pattern.strip("^$") for pattern in (CHANNEL_PATTERN, PLAYLIST_PATTERN))
SUBSCRIPTIONS_PATTERN = f"^(?:{_ONE})(?:,(?:{_ONE}))*$"
# Room given to each allowed subscription in the raw path: the longest one, 4 times (duplicates are tolerated)
_SUBSCRIPTION_ROOM = 35 * 4


def _too_many() -> PydanticCustomError:
    limit = current_config.max_page_items
    return PydanticCustomError(TOO_MANY, "A page holds at most {limit} channels and playlists", {"limit": limit})


def _split(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    # Bounded before it is split, whatever it holds
    if len(value) > current_config.max_page_items * _SUBSCRIPTION_ROOM:
        raise _too_many()
    return split_subscriptions(value)


def _limited(value: list[str]) -> list[str]:
    if len(value) > current_config.max_page_items:
        raise _too_many()
    return value


# Error type raised when an address holds more subscriptions than YOURSS_MAX_PAGE_ITEMS allows
TOO_MANY = "too_many_subscriptions"
# The path of a custom page: subscriptions separated by commas, without duplicate (docs/specs/custom-pages.md §8)
Subscriptions = Annotated[list[Subscription], BeforeValidator(_split), Field(min_length=1), AfterValidator(_limited)]
SUBSCRIPTIONS = TypeAdapter(Subscriptions)
