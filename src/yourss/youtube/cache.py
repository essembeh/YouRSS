from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from time import time

from loguru import logger

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
    except BaseException as error:
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
    except BaseException as error:
        logger.warning("Could not store fallback for {}: {}", key, error)
        tmp.unlink(missing_ok=True)
