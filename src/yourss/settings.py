from pathlib import Path

from loguru import logger

from . import __file__ as app_root
from .schema import AppSettings

templates_folder = Path(app_root).parent / "templates"
static_folder = Path(app_root).parent / "static"

current_config = AppSettings.model_validate({})
logger.debug("Loaded configuration: {}", current_config)

if current_config.cache_folder is not None:
    current_config.cache_folder.mkdir(parents=True, exist_ok=True)
    logger.info("RSS cache enabled: {}", current_config.cache_folder)
