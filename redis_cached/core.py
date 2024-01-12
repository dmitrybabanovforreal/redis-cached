import asyncio
from typing import Callable, TypeVar, Coroutine, Any, ParamSpec
import inspect, functools, hashlib, pickle

from redis_cached.redis import redis, KeyNotFound


_ParamsT = ParamSpec('_ParamsT')
_ReturnT = TypeVar('_ReturnT')
_OriginalFunc = Callable[_ParamsT, Coroutine[Any, Any, _ReturnT]]
_DecoratedFunc = Callable[_ParamsT, Coroutine[Any, Any, _ReturnT]]


def cached(ttl: int, cache_key_salt: str = '') -> Callable[[_OriginalFunc], _DecoratedFunc]:
    """
    Add a cache decorator to a function and specify `ttl` (time to live).
    Optionally, add `cache_key_salt` to avoid cache clashing with same-named functions.

    >>> @cached(5, cache_key_salt='xQGMMpWxfJdxC2_dLVANdg')
    >>> async def add_one(x):
    >>>     return x + 1
    """
    def decorator(func: _OriginalFunc) -> _DecoratedFunc:
        assert inspect.iscoroutinefunction(func), 'Only async functions are supported'

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            assert not args, 'Only keyword arguments are supported'
            key = _get_cache_key(func_name=func.__name__, cache_key_salt=cache_key_salt, **kwargs)
            return await _get_value(key=key, func=func, kwargs=kwargs, ttl=ttl)

        return wrapper

    return decorator


async def invalidate_cache(func_name: str, cache_key_salt: str = None, **kwargs) -> None:
    key = _get_cache_key(func_name=func_name, cache_key_salt=cache_key_salt, **kwargs)
    await redis.delete(key)


def _get_cache_key(func_name: str, cache_key_salt: str, **kwargs) -> str:
    key_parts = f'{func_name}:{cache_key_salt}'.encode('utf-8')
    for k, v in sorted(kwargs.items()):
        key_parts += f':{k}'.encode('utf-8')
        key_parts += pickle.dumps(v)
    key_hash = hashlib.sha256(key_parts).hexdigest()
    return key_hash


async def _get_value(key: str, func: _OriginalFunc, kwargs: dict, ttl: int) -> _ReturnT:
    while 1:
        try:
            return await redis.get_(key)
        except KeyNotFound:
            lock = redis.lock(name=f'{key}_lock', blocking=False)
            if await lock.acquire():
                try:
                    result = await func(**kwargs)
                    await redis.set_(name=key, value=result, ex=ttl)
                finally:
                    await lock.release()
                return result
            else:
                await asyncio.sleep(0.1)
