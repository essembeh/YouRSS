"""What the tests read from the sample users file, so that its ids live there only."""

from pathlib import Path

from pydantic_yaml import parse_yaml_raw_as

from yourss.schema import UsersConfig
from yourss.youtube import is_playlist_id


def sample_playlist() -> str:
    """The playlist of the Music page of the sample users file, a list longer than its feed."""
    config = parse_yaml_raw_as(UsersConfig, Path("samples/users.yaml").read_bytes())
    music = config.users[0].page("Music")
    assert music is not None
    return next(channel for channel in music.channels if is_playlist_id(channel))
