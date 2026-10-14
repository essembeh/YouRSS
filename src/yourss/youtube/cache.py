from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from time import time

from loguru import logger

from ..settings import current_config
from .model import ChannelDescription
from .schema import Feed
from .utils import is_user


def cache_folder() -> Path | None:
    """The cache folder, None when the cache is disabled (docs/specs/disk-cache.md)."""
    return current_config.cache_folder if current_config.cache_enabled else None


def cache_path(folder: Path, key: str, suffix: str) -> Path:
    """Return the cache file path for a given key, sanitizing the key."""
    name = Path(key).name
    if not name:
        raise ValueError(f"Invalid cache key: {key!r}")
    return folder / f"{name}{suffix}"


def _read(path: Path, max_age: timedelta | None) -> bytes | None:
    """The file content when it exists and is younger than ``max_age`` (None: any age). Non-fatal on error."""
    try:
        if not path.is_file():
            return None
        age = time() - path.stat().st_mtime
        if max_age is not None and age >= max_age.total_seconds():
            logger.debug("Cached {} is too old ({:.0f}s)", path.name, age)
            return None
        logger.debug("Reading cached {} ({:.0f}s old)", path.name, age)
        return path.read_bytes()
    except Exception as error:
        logger.warning("Could not read cached {}: {}", path.name, error)
        return None


def _write(path: Path, content: bytes) -> None:
    """Atomically store the content. Non-fatal on error."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(content)
        os.replace(tmp, path)
        logger.debug("Stored {} in the cache", path.name)
    except Exception as error:
        logger.warning("Could not store {} in the cache: {}", path.name, error)
        tmp.unlink(missing_ok=True)


def _drop(path: Path) -> None:
    """Delete the file, if any. Non-fatal on error."""
    try:
        if path.is_file():
            logger.info("Dropping dead cached {}", path.name)
            path.unlink(missing_ok=True)
    except Exception as error:
        logger.warning("Could not drop cached {}: {}", path.name, error)


# --- RSS feeds, keyed by channel or playlist id


def read_cached_feed(folder: Path, key: str, max_age: timedelta) -> Feed | None:
    """The cached feed when it exists and is younger than ``max_age``, else None."""
    content = _read(cache_path(folder, key, ".rss"), max_age)
    if content is None:
        return None
    try:
        return Feed.from_xml(content)
    except Exception as error:
        logger.warning("Could not parse the cached RSS of {}: {}", key, error)
        return None


def write_cached_feed(folder: Path, key: str, content: bytes) -> None:
    _write(cache_path(folder, key, ".rss"), content)


def drop_cached_feed(folder: Path, key: str) -> None:
    _drop(cache_path(folder, key, ".rss"))


# --- Channel descriptions, keyed by channel id and by handle


def _channel_key(name: str) -> str:
    # Handles are case insensitive, channel ids are not
    return name.lower() if is_user(name) else name


def read_cached_channel(folder: Path, name: str, max_age: timedelta | None) -> ChannelDescription | None:
    """The cached description of a channel (``UC…`` or ``@handle``) younger than ``max_age`` (None: any age)."""
    content = _read(cache_path(folder, _channel_key(name), ".json"), max_age)
    if content is None:
        return None
    try:
        return ChannelDescription.model_validate_json(content)
    except Exception as error:
        logger.warning("Could not parse the cached description of {}: {}", name, error)
        return None


def write_cached_channel(folder: Path, name: str, channel: ChannelDescription) -> None:
    """Store the description under the requested name, its channel id and its handle when known."""
    content = channel.model_dump_json().encode()
    for key in {_channel_key(name), channel.channel_id, *([_channel_key(channel.handle)] if channel.handle else [])}:
        _write(cache_path(folder, key, ".json"), content)


def known_channel(name: str) -> ChannelDescription | None:
    """The cached description of a channel whatever its age, without asking Youtube; None without cache."""
    folder = cache_folder()
    return read_cached_channel(folder, name, None) if folder is not None else None
