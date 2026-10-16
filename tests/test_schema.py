from pathlib import Path

from pydantic import ValidationError
from pydantic_yaml import parse_yaml_raw_as
from pytest import mark, raises

from yourss.schema import User, UsersConfig

CHANNELS = ["UCVooVnzQxPSTXTMzSi1s6uw"]


def test_sample_users_file() -> None:
    config = parse_yaml_raw_as(UsersConfig, Path("samples/users.yaml").read_bytes())
    alice, bob, carol = config.users
    assert alice.channels is None and [f.name for f in alice.folders or []] == ["Fun", "Serious"]
    assert alice.folder("Serious") is not None and alice.folder("unknown") is None
    assert bob.folders is None and bob.channels and bob.folder("Fun") is None
    assert carol.password is not None


def test_user_is_flat_or_in_folders() -> None:
    assert User(name="a", channels=CHANNELS).folders is None
    assert User(name="a", folders=[{"name": "skate", "channels": CHANNELS}]).channels is None  # type: ignore[list-item]
    with raises(ValidationError, match="either channels or folders"):
        User(name="a")
    with raises(ValidationError, match="either channels or folders"):
        User(name="a", channels=CHANNELS, folders=[{"name": "skate", "channels": CHANNELS}])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", channels=[])
    with raises(ValidationError):
        User(name="a", folders=[])


@mark.parametrize("name", ["my folder", "-skate", "sk@te", "a" * 33, ""])
def test_name_is_a_slug(name: str) -> None:
    with raises(ValidationError):
        User(name="a", folders=[{"name": name, "channels": CHANNELS}])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name=name, channels=CHANNELS)


def test_folder_names_are_distinct() -> None:
    folders = [{"name": "skate", "channels": CHANNELS}, {"name": "skate", "channels": CHANNELS}]
    with raises(ValidationError, match="distinct names"):
        User(name="a", folders=folders)  # type: ignore[arg-type]
