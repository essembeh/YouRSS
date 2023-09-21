import os

import environ
from loguru import logger

from .utils import parse_channel_names


@environ.config(prefix="YOURSS")
class AppConfig:
    DEFAULT_CHANNELS = environ.var("@jonnygiger")


YOURSS_USER_PREFIX = "YOURSS_USER_"
YOURSS_USERS = {
    k[len(YOURSS_USER_PREFIX) :]: parse_channel_names(v)
    for k, v in os.environ.items()
    if k.startswith(YOURSS_USER_PREFIX)
}

for user, channels in YOURSS_USERS.items():
    logger.info("Found user {}: {}", user, channels)

config = environ.to_config(AppConfig)
