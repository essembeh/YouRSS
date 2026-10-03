from __future__ import annotations

import os
from collections import OrderedDict
from datetime import timedelta
from pathlib import Path
from time import monotonic, time

from loguru import logger

from ..settings import current_config
from .model import ChannelDescription
from .schema import Feed


def cache_path(cache_folder: Path, key: str) -> Path:
    """Return the fallback file path for a given key, sanitizing the key."""
    name = Path(key).name
    assert name, f"Invalid cache key: {key!r}"
    return cache_folder / f"{name}.rss"


def read_stale_feed(cache_folder: Path, key: str, max_age: timedelta) -> Feed | None:
    """Fallback used when the live fetch fails with a Youtube 404.

    This is NOT a cache: feeds are always fetched live. The on-disk copy is only
    served when Youtube returns a transient 404, and only if it is younger than
    ``max_age``. If the file is older, it is considered dead: deleted and None is
    returned. Non-fatal on any error.
    """
    path = cache_path(cache_folder, key)
    try:
        if not path.is_file():
            return None
        age = time() - path.stat().st_mtime
        if age >= max_age.total_seconds():
            logger.info("Dropping dead fallback for {} ({:.0f}s old)", key, age)
            path.unlink(missing_ok=True)
            return None
        logger.info("Serving stale fallback for {} ({:.0f}s old)", key, age)
        return Feed.from_xml(path.read_bytes())
    except Exception as error:
        logger.warning("Could not read fallback for {}: {}", key, error)
        return None


def write_cached_feed(cache_folder: Path, key: str, content: bytes) -> None:
    """Atomically store the raw RSS bytes as the 404 fallback. Non-fatal on error."""
    path = cache_path(cache_folder, key)
    tmp = path.with_suffix(f".rss.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(content)
        os.replace(tmp, path)
        logger.debug("Stored RSS fallback for {}", key)
    except Exception as error:
        logger.warning("Could not store fallback for {}: {}", key, error)
        tmp.unlink(missing_ok=True)


class ChannelCache:
    """
    Small in-memory cache of channel descriptions (id, name, avatar and home
    URLs: a few hundred bytes each). Nothing else is cached: feeds and video
    lists are always fetched live.

    Bounded twice: an entry expires after ``YOURSS_CHANNEL_CACHE_TTL`` (0
    disables the cache) and the least recently used entry is dropped once
    ``max_size`` is reached.
    """

    def __init__(self, max_size: int = 1024) -> None:
        self.max_size = max_size
        self._items: OrderedDict[str, tuple[float, ChannelDescription]] = OrderedDict()

    @staticmethod
    def _key(name: str) -> str:
        # Handles are case insensitive, channel ids are not
        return name.lower() if name.startswith("@") else name

    def get(self, name: str) -> ChannelDescription | None:
        key = self._key(name)
        item = self._items.get(key)
        if item is None:
            return None
        if item[0] <= monotonic():
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return item[1]

    def put(self, name: str, channel: ChannelDescription) -> None:
        ttl = current_config.channel_cache_ttl.total_seconds()
        if ttl <= 0:
            return
        # Known under the requested name and under its channel id
        for key in {self._key(name), channel.channel_id}:
            self._items[key] = (monotonic() + ttl, channel)
            self._items.move_to_end(key)
        while len(self._items) > self.max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


channel_cache = ChannelCache()
