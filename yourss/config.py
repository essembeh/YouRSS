import environ
from loguru import logger

from .users import Theme


@environ.config(prefix="YOURSS")
class AppConfig:
    DEFAULT_CHANNELS = environ.var(default="@jonnygiger")
    REDIS_URL = environ.var(default=None)
    TTL_METADATA = environ.var(converter=int, default=24 * 3600)
    TTL_RSS = environ.var(converter=int, default=3600)
    CLEAN_TITLES = environ.bool_var(default=False)
    THEME = environ.var(default="light", converter=Theme)
    OPEN_PRIMARY = environ.var(default="openModal")
    OPEN_SECONDARY = environ.var(default="openTab")
    USERS_FILE = environ.var(default=None)


current_config = environ.to_config(AppConfig)
logger.debug("Loaded configuration: {}", current_config)
