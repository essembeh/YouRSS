import os
from datetime import timedelta
from pathlib import Path
from tempfile import mkdtemp

from loguru import logger
from pydantic import TypeAdapter

from . import __file__ as app_root
from .schema import AppSettings

_DURATION = TypeAdapter(timedelta)


def iso_duration(value: timedelta) -> str:
    """A duration as the settings write it (PT30M, P2D), `str(timedelta)` has a comma after the days."""
    return str(_DURATION.dump_python(value, mode="json"))


templates_folder = Path(app_root).parent / "templates"
static_folder = Path(app_root).parent / "static"


def check_writable(folder: Path) -> None:
    """Write, read back and delete a probe file: the cache must work before the application starts."""
    probe = folder / f".write-check.{os.getpid()}"
    try:
        probe.write_bytes(b"yourss")
        if probe.read_bytes() != b"yourss":
            raise OSError("read back a different content")
    finally:
        probe.unlink(missing_ok=True)


def setup_cache_folder(config: AppSettings) -> None:
    """Make the cache folder usable, or fail: a cache that was asked for must work (docs/specs/disk-cache.md)."""
    if not config.cache_enabled:
        if config.cache_folder is not None:
            logger.warning("YOURSS_CACHE_FOLDER is set to {} but the cache is disabled", config.cache_folder)
        return
    try:
        if config.cache_folder is None:
            config.cache_folder = Path(mkdtemp(prefix="yourss-"))
            logger.info("Cache enabled in a temporary folder: {}", config.cache_folder)
        else:
            config.cache_folder.mkdir(parents=True, exist_ok=True)
            logger.info("Cache enabled: {}", config.cache_folder)
        check_writable(config.cache_folder)
    except OSError as error:
        raise RuntimeError(f"The cache folder {config.cache_folder} is not usable: {error}") from error
    logger.info(
        "Cache ttl: rss {}, rss fallback {}, metadata {}",
        iso_duration(config.cache_rss_ttl),
        iso_duration(config.cache_rss_fallback_ttl),
        iso_duration(config.cache_metadata_ttl),
    )


current_config = AppSettings()
logger.debug("Loaded configuration: {}", current_config)
setup_cache_folder(current_config)
