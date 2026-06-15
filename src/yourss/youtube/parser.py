"""
Resilient parsers for Youtube's ``ytInitialData`` / ``/youtubei/v1/browse`` payloads.

Youtube periodically reshapes its internal JSON. Historically videos were
described by ``videoRenderer`` / ``richItemRenderer`` nodes; they are now
described by the newer *ViewModel* components (``lockupViewModel``,
``shortsLockupViewModel``).

To survive the next reshape, this module does not hardcode a single deep path.
Instead each field is extracted through a :class:`glom.Coalesce` of candidate
specs tried in order (new format first, legacy format as fallback). Adding
support for a new layout is therefore a one-line change: append a candidate
spec, do not rewrite the parser.

When a payload clearly contains video-like nodes but none of the known parsers
can extract anything, :class:`ScrapingError` is raised so the breakage is
detected immediately instead of silently returning an empty list.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List

from glom import Coalesce, GlomError, glom

from .utils import find_key, iter_key, simple_url


class ScrapingError(RuntimeError):
    """Raised when a payload contains video nodes we can no longer parse."""


def _is_view_count_part(part: Dict[str, Any]) -> bool:
    """
    A metadata part is a counter (views / likes) rather than a date when it
    carries a ``leadingIcon`` (the play-arrow / like glyph) or its
    accessibility label mentions views. Dates never have either.
    """
    if "leadingIcon" in part:
        return True
    label = (part.get("accessibilityLabel") or "").lower()
    return "view" in label


def _published_from_metadata_rows(rows: Any) -> str | None:
    """
    Extract the relative publish date (e.g. ``"4 weeks ago"``) from a
    ``contentMetadataViewModel.metadataRows`` structure.

    A metadata row holds parts such as ``"1.1M views"`` and ``"21 hours ago"``.
    We drop the view/like counters (identified by a ``leadingIcon`` or a
    "views" accessibility label) and keep the remaining text part as the date.
    This handles every observed layout: full ``["90K views", "4 weeks ago"]``,
    compact ``["1.1M"+icon, "21h ago"]``, and members-only ``["2 days ago"]``.

    Prefers a part carrying an ``accessibilityLabel`` (the un-abbreviated date,
    e.g. "21 hours ago" rather than "21h ago"); otherwise falls back to the
    last non-counter part.
    """
    if not isinstance(rows, list):
        return None
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for part in row.get("metadataParts", []):
            if not isinstance(part, dict):
                continue
            if not part.get("text", {}).get("content"):
                continue
            if _is_view_count_part(part):
                continue
            candidates.append(part)
    if not candidates:
        return None
    for part in candidates:
        if part.get("accessibilityLabel"):
            return part["accessibilityLabel"]
    return candidates[-1]["text"]["content"]


def _nested_text(payload: Any, key: str) -> str | None:
    """Find ``key`` anywhere in ``payload`` then read its ``.content`` string."""
    node = find_key(key, payload, dict)
    return node.get("content") if node else None


def _first_source_url(node: Any) -> str | None:
    """First ``sources[].url`` (or ``thumbnails[].url``) found under ``node``."""
    sources = find_key("sources", node, list) or find_key("thumbnails", node, list)
    if sources and isinstance(sources[0], dict):
        return sources[0].get("url")
    return None


class ItemParser(ABC):
    """
    Parser for a single kind of node in a Youtube payload.

    Subclasses declare:

    * ``node_key``: the dict key that wraps the items we care about
      (e.g. ``lockupViewModel``). All matching nodes are located anywhere in
      the payload via a recursive search, so we never depend on the exact
      surrounding container.
    * ``extract``: how to turn one node into a ``VideoDescription`` kwargs dict.
    """

    node_key: str

    def iter_nodes(self, payload: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        yield from iter_key(self.node_key, payload, dict)

    @abstractmethod
    def extract(self, node: Dict[str, Any]) -> Dict[str, Any] | None:
        """Return ``VideoDescription`` kwargs, or ``None`` to skip the node."""

    def parse(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for node in self.iter_nodes(payload):
            try:
                data = self.extract(node)
            except GlomError:
                data = None
            if data is not None:
                out.append(data)
        return out


class LockupVideoParser(ItemParser):
    """New ``lockupViewModel`` videos (also covers live/streams replays)."""

    node_key = "lockupViewModel"

    _TITLE = Coalesce(
        "metadata.lockupMetadataViewModel.title.content",
        default=None,
    )
    _THUMBNAIL = Coalesce(
        "contentImage.thumbnailViewModel.image.sources.0.url",
        default=None,
    )
    _METADATA_ROWS = Coalesce(
        "metadata.lockupMetadataViewModel.metadata"
        ".contentMetadataViewModel.metadataRows",
        default=None,
    )

    def extract(self, node: Dict[str, Any]) -> Dict[str, Any] | None:
        # Only real videos: shorts use shortsLockupViewModel, channels/playlists
        # would have a different contentType.
        content_type = node.get("contentType", "")
        if content_type and "VIDEO" not in content_type:
            return None
        video_id = node.get("contentId")
        if not video_id:
            return None
        thumbnail = glom(node, self._THUMBNAIL)
        return {
            "video_id": video_id,
            "title": glom(node, self._TITLE) or "",
            "published": _published_from_metadata_rows(glom(node, self._METADATA_ROWS)),
            "thumbnail": simple_url(thumbnail) if thumbnail else None,
        }


class LegacyVideoParser(ItemParser):
    """Legacy ``videoRenderer`` videos (kept as a fallback)."""

    node_key = "videoRenderer"

    _TITLE = Coalesce("title.runs.0.text", "title.simpleText", default=None)
    _PUBLISHED = Coalesce("publishedTimeText.simpleText", default=None)
    _THUMBNAIL = Coalesce("thumbnail.thumbnails.0.url", default=None)

    def extract(self, node: Dict[str, Any]) -> Dict[str, Any] | None:
        video_id = node.get("videoId")
        if not video_id:
            return None
        thumbnail = glom(node, self._THUMBNAIL)
        return {
            "video_id": video_id,
            "title": glom(node, self._TITLE) or "",
            "published": glom(node, self._PUBLISHED),
            "thumbnail": simple_url(thumbnail) if thumbnail else None,
        }


class ShortsLockupParser(ItemParser):
    """New ``shortsLockupViewModel`` shorts."""

    node_key = "shortsLockupViewModel"

    _TITLE = Coalesce("overlayMetadata.primaryText.content", default=None)
    _SUBTITLE = Coalesce("overlayMetadata.secondaryText.content", default=None)
    _THUMBNAIL = Coalesce(
        "thumbnailViewModel.image.sources.0.url",
        "onTap.innertubeCommand.reelWatchEndpoint.thumbnail.thumbnails.0.url",
        default=None,
    )
    _VIDEO_ID = Coalesce(
        "onTap.innertubeCommand.reelWatchEndpoint.videoId",
        default=None,
    )

    def extract(self, node: Dict[str, Any]) -> Dict[str, Any] | None:
        video_id = glom(node, self._VIDEO_ID)
        if not video_id:
            # entityId looks like "shorts-shelf-item-<videoId>"
            entity_id = node.get("entityId", "")
            video_id = entity_id.rsplit("-", 1)[-1] if entity_id else None
        if not video_id:
            return None
        thumbnail = glom(node, self._THUMBNAIL)
        return {
            "video_id": video_id,
            "title": glom(node, self._TITLE) or "",
            # Shorts carry no publish date, only a view count.
            "published": glom(node, self._SUBTITLE),
            "thumbnail": simple_url(thumbnail) if thumbnail else None,
        }


class LegacyShortsParser(ItemParser):
    """Legacy ``richItemRenderer`` shorts (kept as a fallback)."""

    node_key = "richItemRenderer"

    def extract(self, node: Dict[str, Any]) -> Dict[str, Any] | None:
        content = node.get("content")
        if not isinstance(content, dict):
            return None
        endpoint = find_key("reelWatchEndpoint", content, dict)
        video_id = endpoint.get("videoId") if endpoint else None
        if not video_id:
            return None
        thumbnail = _first_source_url(find_key("thumbnail", content, dict))
        return {
            "video_id": video_id,
            "title": _nested_text(content, "primaryText") or "",
            "published": _nested_text(content, "secondaryText"),
            "thumbnail": simple_url(thumbnail) if thumbnail else None,
        }


# Parser chains: tried in order, first one that yields items wins.
VIDEO_PARSERS: List[ItemParser] = [LockupVideoParser(), LegacyVideoParser()]
SHORTS_PARSERS: List[ItemParser] = [ShortsLockupParser(), LegacyShortsParser()]


def _looks_like_video_payload(payload: Dict[str, Any]) -> bool:
    """
    True if the payload contains any known video/short node key. Used to tell
    "this channel genuinely has no videos" apart from "Youtube changed its
    structure and we can no longer parse it".
    """
    keys = {p.node_key for p in (*VIDEO_PARSERS, *SHORTS_PARSERS)}
    for key in keys:
        if next(iter_key(key, payload, dict), None) is not None:
            return True
    return False


def parse_items(
    payload: Dict[str, Any], parsers: List[ItemParser]
) -> List[Dict[str, Any]]:
    """
    Run ``parsers`` in order and return the first non-empty result.

    Raises :class:`ScrapingError` if the payload looks like it should contain
    videos but no parser could extract a single item.
    """
    for parser in parsers:
        if items := parser.parse(payload):
            return items
    if _looks_like_video_payload(payload):
        raise ScrapingError(
            "Youtube payload contains video-like nodes but none could be "
            "parsed: the page structure has likely changed."
        )
    return []
