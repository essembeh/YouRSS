from typing import Annotated

from fastapi import Path

from ..youtube.utils import CHANNEL_PATTERN, PLAYLIST_PATTERN, USER_PATTERN

UserId = Annotated[str, Path(pattern=USER_PATTERN)]
ChannelId = Annotated[str, Path(pattern=CHANNEL_PATTERN)]
Playlist_Id = Annotated[str, Path(pattern=PLAYLIST_PATTERN)]
