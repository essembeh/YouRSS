import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Iterable

from loguru import logger
from redis import Redis

from .config import config
from .model import RssFeed
from .youtube import youtube_get_metadata, youtube_get_rss_feed


def create_redis(url: str | None) -> Redis | None:
    if url is not None:
        out = Redis(host=url)
        if out.ping():
            logger.info("Redis ping OK: {}", out)
            return out
        else:
            logger.warning("Redis ping failed: {}", out)
    else:
        logger.info("No redis cache defined")


redis = create_redis(config.REDIS_URL)


def redis_cached(ttl: int | None = None):
    """
    ttl is in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Test is redis is declared
            if redis is None:
                return func(*args, **kwargs)

            # Test if redis is ready
            if not redis.ping():
                logger.warning("Redis ping failed: {}", redis)
                return func(*args, **kwargs)

            # Generate the cache key from the function's arguments.
            key_parts = [func.__name__] + list(args)
            key = ":".join(key_parts)
            result = redis.get(key)

            if result is None:
                # Run the function and cache the result for next time.
                value = func(*args, **kwargs)
                value_json = json.dumps(value)
                redis.set(key, value_json, ex=ttl)
            else:
                # Skip the function entirely and use the cached value instead.
                value_json = result.decode("utf-8")
                value = json.loads(value_json)

            return value

        return wrapper

    return decorator


@redis_cached(ttl=14400)
def get_avatar_url(name: str) -> str | None:
    return youtube_get_metadata(name).avatar_url


def get_rssfeeds(names: Iterable[str], workers: int = 4) -> dict[str, RssFeed | None]:
    @redis_cached(ttl=3600)
    def get_response_text(name) -> str:
        resp = youtube_get_rss_feed(name)
        resp.raise_for_status()
        return resp.text

    out = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        jobs = {executor.submit(get_response_text, x): x for x in set(names)}
        for job in as_completed(jobs):
            name = jobs[job]
            try:
                out[name] = RssFeed.fromstring(job.result())
            except BaseException:
                out[name] = None
    return out
