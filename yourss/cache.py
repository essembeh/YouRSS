import json
from functools import wraps

from loguru import logger
from redis import Redis

from .config import current_config
from .youtube import YoutubeWebClient


def _redis_connect(url: str | None) -> Redis | None:
    if isinstance(url, str) and len(url) > 0:
        out = Redis.from_url(url)
        if out.ping():
            logger.info("Redis ping OK: {}", out)
            return out
        else:
            logger.warning("Redis ping failed: {}", out)
    else:
        logger.info("No redis cache defined")


current_redis = _redis_connect(current_config.REDIS_URL)


def redis_cached(ttl: int | None = None):
    """
    ttl is in seconds
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Test is redis is declared
            if current_redis is None:
                return await func(*args, **kwargs)

            # Test if redis is ready
            if not current_redis.ping():
                logger.warning("Redis ping failed: {}", current_redis)
                return await func(*args, **kwargs)

            # Generate the cache key from the function's arguments.
            key_parts = [func.__name__] + list(map(str, args))
            key = ":".join(key_parts)
            result = current_redis.get(key)

            if result is None:
                # Run the function and cache the result for next time.
                value = await func(*args, **kwargs)
                value_json = json.dumps(value)
                current_redis.set(key, value_json, ex=ttl)
            else:
                # Skip the function entirely and use the cached value instead.
                value_json = result.decode("utf-8")
                value = json.loads(value_json)

            return value

        return wrapper

    return decorator


class YoutubeWebClientWithCache(YoutubeWebClient):
    @redis_cached(ttl=current_config.TTL_AVATAR)
    async def get_avatar_url(self, name: str) -> str | None:
        return await super().get_avatar_url(name)

    @redis_cached(ttl=current_config.TTL_RSS)
    async def get_rss_xml(self, name: str) -> str:
        return await super().get_rss_xml(name)
