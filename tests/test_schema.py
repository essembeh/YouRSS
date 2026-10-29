from pathlib import Path
from typing import Any

from pydantic import ValidationError
from pydantic_yaml import parse_yaml_raw_as
from pytest import mark, raises

from yourss.schema import User, UsersConfig

CHANNELS = ["UCVooVnzQxPSTXTMzSi1s6uw"]


def page(name: str, **fields: Any) -> dict[str, Any]:
    return {"name": name, "channels": CHANNELS, **fields}


def test_sample_users_file() -> None:
    config = parse_yaml_raw_as(UsersConfig, Path("samples/users.yaml").read_bytes())
    alice, bob = config.users
    assert [page.name for page in alice.pages] == ["Homepage", "Cards", "Podcast", "Music"]
    assert [page.publish for page in alice.pages] == ["fun", None, None, "music"]
    assert [page.warmup for page in config.pages] == [True, False, True, True, True]
    assert alice.page("Cards") is not None and alice.page("unknown") is None
    assert [page.name for page in bob.pages] == ["Homepage"] and bob.password is not None
    assert [page.name for page in config.pages] == ["Homepage", "Cards", "Podcast", "Music", "Homepage"]
    assert config.public_page("skate") is bob.pages[0]
    assert config.public_page("fun") is alice.pages[0]
    assert config.public_page("Cards") is None and config.public_page("Homepage") is None


def test_user_pages() -> None:
    # A page is a mapping with its name and channels
    with raises(ValidationError):
        User(name="a", pages=["skate"])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[{"name": "skate"}])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[page("skate", channels=[])])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[])
    with raises(ValidationError, match="pages of a user have distinct names"):
        User(name="a", pages=[page("skate"), page("skate")])  # type: ignore[list-item]


@mark.parametrize("name", ["my page", "-skate", "sk@te", "a" * 33, ""])
def test_name_is_a_slug(name: str) -> None:
    with raises(ValidationError):
        User(name="a", pages=[page(name)])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[page("skate", publish=name)])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name=name, pages=[page("skate")])  # type: ignore[list-item]


def test_file_names_are_checked() -> None:
    with raises(ValidationError, match="users have distinct names"):
        UsersConfig(users=[{"name": "a", "pages": [page("skate")]}] * 2)  # type: ignore[list-item]
    # Two users may name a page alike, not publish it under the same name
    UsersConfig(users=[{"name": "a", "pages": [page("skate")]}, {"name": "b", "pages": [page("skate")]}])  # type: ignore[list-item]
    users: list[Any] = [
        {"name": "a", "pages": [page("skate", publish="skate")]},
        {"name": "b", "pages": [page("board", publish="skate")]},
    ]
    with raises(ValidationError, match="published pages have distinct names"):
        UsersConfig(users=users)
    with raises(ValidationError):
        UsersConfig(users=[])
    # Unknown keys are refused: a typo must not leave a page unpublished
    with raises(ValidationError, match="pubish"):
        User(name="a", pages=[page("m", pubish="m")])  # type: ignore[list-item]
    # The shapes of 0.83 (top level pages, a user listing them by name, visible, label) are refused
    with raises(ValidationError):
        UsersConfig(pages=[page("skate")], users=[{"name": "a", "pages": [page("skate")]}])  # type: ignore[call-arg, list-item]
    with raises(ValidationError):
        User(name="a", pages=[page("skate", visible=False)])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[page("skate", label="Skate")])  # type: ignore[list-item]
