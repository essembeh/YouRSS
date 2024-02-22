from __future__ import annotations

import pickle
from datetime import timedelta
from typing import Any, Optional, Type, TypeVar

from attr import dataclass
from loguru import logger
from redis.asyncio import Redis as AsyncRedis

T = TypeVar("T")


@dataclass(kw_only=True)
class YourssCache:
    force_renew: bool = False

    async def read(self, key: str, clazz: Type[T]) -> Optional[T]:
        return None

    async def write(self, key: str, data: Any, ttl: int) -> bool:
        return False


class NoCache(YourssCache):
    ...


@dataclass(kw_only=True)
class RedisCache(YourssCache):
    redis: AsyncRedis

    async def read(self, key: str, clazz: Type[T]) -> Optional[T]:
        if self.force_renew:
            logger.debug(f"Force redis cache renew for {key}")
        elif (data := await self.redis.get(key)) is not None:
            logger.debug(f"Found key {key} in cache")
            out = pickle.loads(data)
            assert isinstance(out, clazz)
            return out
        else:
            logger.debug(f"Cannot find {key} in cache")
        return await super().read(key, clazz)

    async def write(self, key: str, data: Any, ttl: int) -> bool:
        out = await self.redis.set(key, pickle.dumps(data), ex=timedelta(seconds=ttl))
        logger.debug(f"Cache key {key}: {out}")
        return out is True


async def create_cache(
    redis_url: str | None = None, force_renew: bool = False
) -> YourssCache:
    if redis_url is not None:
        try:
            redis = AsyncRedis.from_url(redis_url)
            if await redis.ping():
                logger.info("Use Redis Cache: {}", redis_url)
                return RedisCache(redis=redis, force_renew=force_renew)
        except BaseException as error:
            logger.error("Could not configure Redis Cache: {}", error)
    return NoCache(force_renew=force_renew)
