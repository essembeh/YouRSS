import os

import environ
from loguru import logger

from .utils import parse_channel_names


@environ.config(prefix="YOURSS")
class AppConfig:
    DEFAULT_CHANNELS = environ.var("@jonnygiger")
    REDIS_URL = environ.var(default=None)
    TTL_AVATAR = environ.var(converter=int, default=24 * 3600)
    TTL_RSS = environ.var(converter=int, default=3600)
    CLEAN_TITLES = environ.bool_var(default=False)
    THEME = environ.var("light")


YOURSS_USER_PREFIX = "YOURSS_USER_"
YOURSS_USERS = {
    k[len(YOURSS_USER_PREFIX) :]: parse_channel_names(v)
    for k, v in os.environ.items()
    if k.startswith(YOURSS_USER_PREFIX)
}

current_config = environ.to_config(AppConfig)

logger.debug("Loaded configuration: {}", current_config)
for user, channels in YOURSS_USERS.items():
    logger.info("Found user {}: {}", user, channels)
