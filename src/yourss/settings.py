from pathlib import Path

from loguru import logger

from . import __file__ as app_root
from .schema import AppSettings

templates_folder = Path(app_root).parent / "templates"
static_folder = Path(app_root).parent / "static"

current_config = AppSettings()
logger.debug("Loaded configuration: {}", current_config)
