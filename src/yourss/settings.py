from pathlib import Path
from tempfile import mkdtemp

from loguru import logger

from . import __file__ as app_root
from .schema import AppSettings

templates_folder = Path(app_root).parent / "templates"
static_folder = Path(app_root).parent / "static"


def setup_cache_folder(config: AppSettings) -> None:
    """Make the RSS cache folder usable: create the given one, or pick a temporary one."""
    if not config.cache_enabled:
        if config.cache_folder is not None:
            logger.warning("YOURSS_CACHE_FOLDER is set to {} but the RSS cache is disabled", config.cache_folder)
        return
    if config.cache_folder is None:
        config.cache_folder = Path(mkdtemp(prefix="yourss-"))
        logger.info("RSS cache enabled in a temporary folder: {}", config.cache_folder)
    else:
        config.cache_folder.mkdir(parents=True, exist_ok=True)
        logger.info("RSS cache enabled: {}", config.cache_folder)
    logger.info("RSS cache ttl: {}, fallback ttl: {}", config.cache_ttl, config.cache_fallback_ttl)


current_config = AppSettings()
logger.debug("Loaded configuration: {}", current_config)
setup_cache_folder(current_config)
