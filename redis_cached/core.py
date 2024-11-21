from typing import Callable, TypeVar, Coroutine, Any, ParamSpec, TypeAlias
import asyncio, inspect, functools, hashlib, pickle, os, logging

from redis.asyncio.client import Redis
from redis.exceptions import OutOfMemoryError

from redis_cached.utils import lock_release_retry


logger = logging.getLogger('redis_cached')
_P = ParamSpec('_P')
_R = TypeVar('_R')
_AsyncFunc: TypeAlias = Callable[_P, Coroutine[Any, Any, _R]]


class KeyNotFound(Exception):
    pass


class Cache:
    def __init__(
        self,
        cache_key_salt: str = '',
        redis_: Redis = None,
        cache_refresh_lock_timeout: int = 5
    ):
        self.cache_key_salt = cache_key_salt
        self.cache_refresh_lock_timeout = cache_refresh_lock_timeout
        if redis_:
            assert isinstance(redis_, Redis), '`redis_` has to be an instance of redis.asyncio.client.Redis'
            self.redis = redis_
        else:
            host = os.getenv('REDIS_HOST')
            assert host, 'REDIS_HOST env var not found'
            self.redis = Redis(
                host=host,
                port=int(os.getenv('REDIS_PORT') or 6379),
                db=int(os.getenv('REDIS_DB') or 0),
            )

    def cached(self, ttl: int):
        """
        Add a cache decorator to a function and specify `ttl` (time to live).
        Optionally, add `cache_key_salt` to avoid cache clashing with same-named functions.

        >>> cache = Cache(cache_key_salt='xfJdxC')
        >>>
        >>> @cache.cached(5)
        >>> async def add_one(x):
        >>>     return x + 1
        """
        def decorator(func: _AsyncFunc) -> _AsyncFunc:
            assert inspect.iscoroutinefunction(func), 'Only async functions are supported'

            @functools.wraps(func)
            async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                assert not args, 'Only keyword arguments are supported'
                key = self._get_cache_key(func_name=func.__name__, **kwargs)
                return await self._get_value(key=key, func=func, kwargs=kwargs, ttl=ttl)

            return wrapper

        return decorator

    async def invalidate_cache(self, func_name: str, **kwargs) -> None:
        key = self._get_cache_key(func_name=func_name, **kwargs)
        await self.redis.delete(key)

    def _get_cache_key(self, func_name: str, **kwargs) -> str:
        key_parts = f'{func_name}:{self.cache_key_salt}'.encode('utf-8')
        for k, v in sorted(kwargs.items()):
            key_parts += f':{k}'.encode('utf-8')
            key_parts += pickle.dumps(v)
        key_hash = hashlib.sha256(key_parts).hexdigest()
        return key_hash

    async def _get_value(self, key: str, func: _AsyncFunc, kwargs: dict, ttl: int) -> _R:
        while True:
            try:
                return await self._redis_get(key)
            except KeyNotFound:
                lock_key = f'{key}_lock'
                lock = self.redis.lock(name=lock_key, blocking=False, timeout=self.cache_refresh_lock_timeout)
                if await lock.acquire():
                    try:
                        result = await func(**kwargs)
                        await self._redis_set(name=key, value=result, ex=ttl)
                        return result
                    finally:
                        if not await lock_release_retry(lock):
                            logger.error(f'Failed to release cache refresh lock for {lock_key}')
                else:
                    await asyncio.sleep(0.1)

    async def _redis_get(self, name: str) -> Any:
        res = await self.redis.get(name)
        if not res:
            raise KeyNotFound()
        return pickle.loads(res)

    async def _redis_set(self, name: str, value: Any, ex: None | int = None) -> None:
        value = pickle.dumps(value)
        try:
            await self.redis.set(name=name, value=value, ex=ex)
        except OutOfMemoryError:
            logger.warning('Redis returned OutOfMemoryError; the result has not been cached.')
