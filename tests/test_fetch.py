from datetime import UTC, datetime, timedelta
from pathlib import Path

from httpx import ConnectError, HTTPStatusError, ReadTimeout, Request, Response
from pydantic import ValidationError
from pytest import MonkeyPatch, fixture, mark

from yourss.async_utils import Kind, State, SubscriptionStatus, async_fetch, reason_of
from yourss.routers.utils import age_text, canonical_names, fetch_summary, page_entries
from yourss.settings import current_config
from yourss.youtube import ChannelDescription, Feed, ScrapingError, YoutubeApi
from yourss.youtube.cache import write_cached_channel

SAMPLES_FOLDER = Path(__file__).parent / "data"
CHANNEL_ID = "UCVooVnzQxPSTXTMzSi1s6uw"
PLAYLIST_ID = "PLw-vK1_d04zZCal3yMX_T23h5nDJ2toTk"
OTHER_ID = "UCQsmxaMzYr76Yd1iqMEq8TA"
HANDLE = "@JonnyGiger"
JONNY = ChannelDescription(channel_id=CHANNEL_ID, name="Jonny Giger", avatar="https://yt3/abc", handle=HANDLE)


def _http_error(status: int) -> HTTPStatusError:
    request = Request("GET", "https://www.youtube.com/feeds/videos.xml")
    return HTTPStatusError(str(status), request=request, response=Response(status, request=request))


def _feed(key: str, cached_at: datetime | None = None) -> Feed:
    out = Feed.from_xml((SAMPLES_FOLDER / f"{key}.xml").read_bytes())
    out._cached_at = cached_at
    return out


@fixture
def api(monkeypatch: MonkeyPatch, tmp_path: Path) -> YoutubeApi:
    """A YoutubeApi serving the sample feeds, failing on anything else, on an empty enabled cache."""
    monkeypatch.setattr(current_config, "cache_enabled", True)
    monkeypatch.setattr(current_config, "cache_folder", tmp_path)
    monkeypatch.setattr(current_config, "cache_rss_ttl", timedelta(minutes=30))
    instance = YoutubeApi()

    async def get_channel_rss(channel_id: str, *, refresh: bool = False) -> Feed:
        if channel_id == CHANNEL_ID:
            return _feed(channel_id)
        raise _http_error(404)

    async def get_playlist_rss(playlist_id: str, *, refresh: bool = False) -> Feed:
        if playlist_id == PLAYLIST_ID:
            return _feed(playlist_id)
        raise _http_error(404)

    async def get_channel(name: str) -> ChannelDescription:
        if name.lower() == HANDLE.lower():
            return JONNY
        raise _http_error(404)

    monkeypatch.setattr(instance, "get_channel_rss", get_channel_rss)
    monkeypatch.setattr(instance, "get_playlist_rss", get_playlist_rss)
    monkeypatch.setattr(instance, "get_channel", get_channel)
    return instance


# --- async_fetch


async def test_feeds_are_asked_without_metadata(monkeypatch: MonkeyPatch, api: YoutubeApi) -> None:
    async def never(name: str) -> ChannelDescription:
        raise AssertionError("no channel page is scraped while building a page")

    monkeypatch.setattr(api, "get_channel", never)
    statuses = await async_fetch([PLAYLIST_ID, CHANNEL_ID], api)

    assert [(s.name, s.kind, s.state) for s in statuses] == [
        (PLAYLIST_ID, Kind.PLAYLIST, State.OK),
        (CHANNEL_ID, Kind.CHANNEL, State.OK),
    ]
    channel = statuses[1].channel
    # Described from the feed: name and id, no avatar
    assert channel is not None and channel.channel_id == CHANNEL_ID and channel.name and not channel.avatar
    assert statuses[1].label == channel.name
    assert statuses[0].label == statuses[0].feed.title  # type: ignore[union-attr]


async def test_cached_metadata_completes_the_feed(api: YoutubeApi, tmp_path: Path) -> None:
    write_cached_channel(tmp_path, CHANNEL_ID, JONNY)
    (status,) = await async_fetch([CHANNEL_ID], api)
    assert status.channel == JONNY


async def test_failed_feed(api: YoutubeApi, tmp_path: Path) -> None:
    statuses = await async_fetch([OTHER_ID, CHANNEL_ID], api)

    failed, ok = statuses
    assert failed.state is State.FAILED and failed.feed is None and failed.channel is None
    assert failed.reason == "Youtube does not serve this feed right now"
    assert failed.label is None and failed.id == OTHER_ID and failed.initial == "U"
    assert ok.state is State.OK

    # The cache may still name a failed channel
    write_cached_channel(tmp_path, OTHER_ID, ChannelDescription(channel_id=OTHER_ID, name="Other"))
    (failed, _) = await async_fetch([OTHER_ID, CHANNEL_ID], api)
    assert failed.channel is not None and failed.label == "Other"


async def test_stale_feed(monkeypatch: MonkeyPatch, api: YoutubeApi) -> None:
    async def get_channel_rss(channel_id: str, *, refresh: bool = False) -> Feed:
        return _feed(CHANNEL_ID, cached_at=datetime.now(UTC) - timedelta(hours=3))

    monkeypatch.setattr(api, "get_channel_rss", get_channel_rss)
    (status,) = await async_fetch([CHANNEL_ID], api)

    assert status.state is State.STALE and status.feed is not None
    assert status.age is not None and timedelta(hours=3) <= status.age < timedelta(hours=3, minutes=1)

    # A copy younger than the ttl is a plain hit
    monkeypatch.setattr(current_config, "cache_rss_ttl", timedelta(hours=4))
    (status,) = await async_fetch([CHANNEL_ID], api)
    assert status.state is State.OK and status.age is None


async def test_handles(api: YoutubeApi) -> None:
    statuses = await async_fetch([HANDLE, "@unknown"], api)

    resolved, unresolved = statuses
    assert resolved.state is State.OK and resolved.channel == JONNY and resolved.id == CHANNEL_ID
    assert unresolved.state is State.FAILED and unresolved.feed is None and unresolved.id == "@unknown"
    assert unresolved.initial == "U"
    assert canonical_names(statuses) == [CHANNEL_ID, "@unknown"]


@mark.parametrize(
    "error,reason",
    [
        (_http_error(404), "Youtube does not serve this feed right now"),
        (_http_error(503), "Youtube answered an error"),
        (ReadTimeout("slow"), "Youtube did not answer in time"),
        (ConnectError("down"), "Youtube could not be reached"),
        (ScrapingError("layout"), "Youtube answered something unexpected"),
        (ValueError("anything"), "Could not be fetched"),
    ],
)
def test_reason_of(error: Exception, reason: str) -> None:
    assert reason_of(error) == reason


def test_reason_of_validation_error() -> None:
    try:
        ChannelDescription.model_validate({})
    except ValidationError as error:
        assert reason_of(error) == "Youtube answered something unexpected"


# --- page_entries and fetch_summary


def _status(
    name: str,
    state: State = State.OK,
    label: str | None = None,
    age: timedelta | None = None,
    reason: str | None = None,
) -> SubscriptionStatus:
    kind = Kind.PLAYLIST if name.startswith("PL") else Kind.CHANNEL
    feed = None
    channel = None
    if label is not None:
        if kind is Kind.PLAYLIST:
            feed = _feed(PLAYLIST_ID)
            feed.title = label
        else:
            channel = ChannelDescription(channel_id=name if name.startswith("UC") else CHANNEL_ID, name=label)
    return SubscriptionStatus(name=name, kind=kind, state=state, feed=feed, channel=channel, age=age, reason=reason)


def test_page_entries_order() -> None:
    statuses = [
        _status("PL" + "b" * 32, label="Zeta list"),
        _status("UC" + "z" * 22, State.FAILED),
        _status("UC" + "b" * 22, label="bob"),
        _status("UC" + "a" * 22, State.STALE, label="Alice", age=timedelta(hours=1)),
        _status("PL" + "a" * 32, State.FAILED),
        _status("UC" + "c" * 22, State.FAILED, label="Carol"),
        _status("@dave", State.FAILED),
    ]
    assert [s.label or s.name for s in page_entries(statuses)] == [
        "Alice",  # stale, keeps its place
        "bob",
        "Carol",  # failed but known, keeps its place
        "Zeta list",
        "@dave",  # nothing known: raw names last, by name
        "PL" + "a" * 32,
        "UC" + "z" * 22,
    ]


def test_fetch_summary_nothing_to_say() -> None:
    assert fetch_summary([_status("UC" + "a" * 22, label="Alice")]) is None
    assert fetch_summary([]) is None


def test_fetch_summary_some_failed() -> None:
    statuses = [_status(f"UC{i:022d}", label=f"Channel {i}") for i in range(5)]
    statuses += [_status("UC" + "x" * 22, State.FAILED, reason="Youtube answered an error")]
    statuses += [_status("@bob", State.FAILED, label="Bob", reason="Youtube did not answer in time")]
    summary = fetch_summary(statuses)
    assert summary is not None
    assert summary.line == "2 of 7 subscriptions could not be refreshed."
    assert summary.details == [
        ("UC" + "x" * 22, "Youtube answered an error"),
        ("Bob", "Youtube did not answer in time"),
    ]


def test_fetch_summary_most_failed() -> None:
    statuses = [_status(f"UC{i:022d}", State.FAILED, reason="r") for i in range(2)]
    statuses += [
        _status("UC" + "a" * 22, label="Alice"),
        _status("UC" + "b" * 22, State.STALE, label="Bob", age=timedelta(hours=2)),
    ]
    summary = fetch_summary(statuses)
    assert summary is not None
    assert summary.line == (
        "Youtube seems unavailable right now: most subscriptions could not be refreshed, 1 other shows a cached copy."
    )
    assert summary.details == []


def test_fetch_summary_stale_only() -> None:
    statuses = [
        _status("UC" + "a" * 22, State.STALE, label="Alice", age=timedelta(hours=3, minutes=10)),
        _status("UC" + "b" * 22, State.STALE, label="Bob", age=timedelta(minutes=50)),
        _status("UC" + "c" * 22, label="Carol"),
    ]
    summary = fetch_summary(statuses)
    assert summary is not None
    assert summary.line == "2 subscriptions show a cached copy, up to 3 hours old."
    assert summary.details == [("Alice", "cached copy, 3 hours old"), ("Bob", "cached copy, 50 minutes old")]

    summary = fetch_summary(statuses[1:])
    assert summary is not None
    assert summary.line == "1 subscription shows a cached copy, 50 minutes old."


def test_fetch_summary_failed_and_stale() -> None:
    statuses = [_status(f"UC{i:022d}", label=f"Channel {i}") for i in range(4)]
    statuses += [_status("UC" + "x" * 22, State.FAILED, reason="r")]
    statuses += [_status("UC" + "s" * 22, State.STALE, label="Sam", age=timedelta(hours=1))]
    summary = fetch_summary(statuses)
    assert summary is not None
    assert summary.line == "1 of 6 subscriptions could not be refreshed, 1 other shows a cached copy."


@mark.parametrize(
    "age,text",
    [
        (timedelta(seconds=30), "less than a minute"),
        (timedelta(minutes=1), "1 minute"),
        (timedelta(minutes=50), "50 minutes"),
        (timedelta(hours=1, minutes=59), "1 hour"),
        (timedelta(hours=26), "26 hours"),
        (timedelta(days=2), "2 days"),
    ],
)
def test_age_text(age: timedelta, text: str) -> None:
    assert age_text(age) == text
