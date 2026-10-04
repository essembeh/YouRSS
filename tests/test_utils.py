from pytest import mark

from yourss.routers.utils import split_subscriptions
from yourss.youtube import parse_channel_reference, parse_video_reference

CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"


@mark.parametrize(
    "text,expected",
    [
        (CHANNEL_ID, CHANNEL_ID),
        ("  @JonnyGiger ", "@JonnyGiger"),
        ("@some.name-1", "@some.name-1"),
        ("https://www.youtube.com/@JonnyGiger", "@JonnyGiger"),
        ("youtube.com/@JonnyGiger/videos?view=0", "@JonnyGiger"),
        (f"https://m.youtube.com/channel/{CHANNEL_ID}/featured", CHANNEL_ID),
        ("https://www.youtube.com/@%E3%83%86%E3%82%B9%E3%83%88", "@テスト"),
        ("https://www.youtube.com/watch?v=q5IMA244HXw", None),
        ("https://example.org/@JonnyGiger", None),
        ("jonny giger", None),
        ("", None),
    ],
)
def test_parse_channel_reference(text: str, expected: str | None) -> None:
    assert parse_channel_reference(text) == expected


@mark.parametrize(
    "text,expected",
    [
        ("https://www.youtube.com/watch?v=q5IMA244HXw", "q5IMA244HXw"),
        ("youtube.com/watch?list=PLx&v=q5IMA244HXw&t=12s", "q5IMA244HXw"),
        ("https://youtu.be/q5IMA244HXw?si=abc", "q5IMA244HXw"),
        ("https://www.youtube.com/shorts/q5IMA244HXw", "q5IMA244HXw"),
        ("https://m.youtube.com/live/q5IMA244HXw", "q5IMA244HXw"),
        ("https://www.youtube.com/embed/q5IMA244HXw", "q5IMA244HXw"),
        ("https://example.org/watch?v=q5IMA244HXw", None),
        ("https://www.youtube.com/watch?v=short", None),
        ("q5IMA244HXw", None),
        ("https://www.youtube.com/@JonnyGiger", None),
    ],
)
def test_parse_video_reference(text: str, expected: str | None) -> None:
    assert parse_video_reference(text) == expected


def test_split_subscriptions() -> None:
    assert split_subscriptions(" @b, @a,,@b ,UCx") == ["@b", "@a", "UCx"]
