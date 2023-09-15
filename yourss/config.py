import os

import environ
from loguru import logger


@environ.config(prefix="YOURSS")
class AppConfig:
    EMBED_URL = environ.var("https://www.youtube-nocookie.com/embed/")
    # EMBED_URL = environ.var("https://www.youtube.com/embed/")
    DEFAULT_CHANNELS = environ.var("@jonnygiger")


YOURSS_USER_PREFIX = "YOURSS_USER_"
YOURSS_USERS = {
    k[len(YOURSS_USER_PREFIX) :]: v.split(",")
    for k, v in os.environ.items()
    if k.startswith(YOURSS_USER_PREFIX)
}

for user, channels in YOURSS_USERS.items():
    logger.info("Found user {}: {}", user, channels)
