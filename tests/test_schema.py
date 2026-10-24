from pathlib import Path
from typing import Any

from pydantic import ValidationError
from pydantic_yaml import parse_yaml_raw_as
from pytest import mark, raises

from yourss.schema import User, UsersConfig

CHANNELS = ["UCVooVnzQxPSTXTMzSi1s6uw"]
PAGES: list[Any] = [{"name": "skate", "channels": CHANNELS}, {"name": "magic", "visible": False, "channels": CHANNELS}]


def test_sample_users_file() -> None:
    config = parse_yaml_raw_as(UsersConfig, Path("samples/users.yaml").read_bytes())
    assert [page.name for page in config.pages] == ["fun", "cards", "podcast", "music"]
    assert [page.visible for page in config.pages] == [True, False, True, True]
    alice, bob = config.users
    assert [page.name for page in alice.pages] == ["fun", "cards", "podcast", "music"]
    assert [page.title for page in alice.pages] == ["fun", "Card magic", "podcast", "music"]
    assert alice.page("cards") is not None and alice.page("unknown") is None
    assert [page.name for page in bob.pages] == ["podcast", "fun"] and bob.password is not None


def test_user_pages_with_an_optional_label() -> None:
    user = User(name="a", pages=[{"name": "skate"}, {"name": "magic", "label": "Card magic"}])  # type: ignore[list-item]
    assert [(page.name, page.label, page.title) for page in user.pages] == [
        ("skate", None, "skate"),
        ("magic", "Card magic", "Card magic"),
    ]
    # A page is a mapping with its name, never a bare string
    with raises(ValidationError):
        User(name="a", pages=["skate"])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[])
    with raises(ValidationError, match="lists a page once"):
        User(name="a", pages=[{"name": "skate"}, {"name": "skate"}])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[{"name": "skate", "label": ""}])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name="a", pages=[{"name": "skate", "label": "   "}])  # type: ignore[list-item]
    assert User(name="a", pages=[{"name": "skate", "label": " Skate "}]).pages[0].title == "Skate"  # type: ignore[list-item]


@mark.parametrize("name", ["my page", "-skate", "sk@te", "a" * 33, ""])
def test_name_is_a_slug(name: str) -> None:
    with raises(ValidationError):
        UsersConfig(pages=[{"name": name, "channels": CHANNELS}])  # type: ignore[list-item]
    with raises(ValidationError):
        User(name=name, pages=[{"name": "skate"}])  # type: ignore[list-item]


def test_file_names_are_checked() -> None:
    with raises(ValidationError, match="pages have distinct names"):
        UsersConfig(pages=[*PAGES, {"name": "skate", "channels": CHANNELS}])  # type: ignore[list-item]
    with raises(ValidationError, match="users have distinct names"):
        UsersConfig(pages=PAGES, users=[{"name": "a", "pages": [{"name": "skate"}]}] * 2)  # type: ignore[list-item]
    with raises(ValidationError, match="unknown page: foot"):
        UsersConfig(pages=PAGES, users=[{"name": "a", "pages": [{"name": "foot"}]}])  # type: ignore[list-item]
    with raises(ValidationError):
        UsersConfig(pages=[])
    # Unknown keys are refused: a typo must not make a hidden page public
    with raises(ValidationError, match="visibile"):
        UsersConfig(pages=[{"name": "m", "visibile": False, "channels": CHANNELS}])  # type: ignore[list-item]
    # The shapes of 0.82 (channels or folders on a user) are refused
    with raises(ValidationError):
        UsersConfig(pages=PAGES, users=[{"name": "a", "channels": CHANNELS}])  # type: ignore[list-item]
    with raises(ValidationError):
        UsersConfig(users=[{"name": "a", "folders": [{"name": "b", "channels": CHANNELS}]}])  # type: ignore[call-arg, list-item]
