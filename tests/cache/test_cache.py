import asyncio, datetime

import pytest
from pydantic import BaseModel

from redis_cached.redis import redis
from redis_cached.core import _get_cache_key
from redis_cached import cached, invalidate_cache
from tests.utils import random_string


@pytest.mark.asyncio(scope="session")
async def test_redis_connection():
    key = random_string()
    data = random_string()
    await redis.set(key, data)
    assert await redis.get(key) == data


@pytest.mark.asyncio(scope="session")
async def test_cache(random_int: int):

    @cached(5)
    async def plus_random(x):
        return x + random_int

    result = await plus_random(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='plus_random', cache_key_salt='', x=2)
    value = await redis.get(key)
    assert value == 2 + random_int

    assert await plus_random(x=2) == 2 + random_int

    doctored_value = random_string()
    await redis.set(key, doctored_value, ex=5)

    cached_result = await plus_random(x=2)
    assert cached_result == doctored_value


@pytest.mark.asyncio(scope="session")
async def test_cache_with_salt(random_int: int, salt: str):

    @cached(5, cache_key_salt=salt)
    async def plus_random(x):
        return x + random_int

    result = await plus_random(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='plus_random', cache_key_salt=salt, x=2)
    value = await redis.get(key)
    assert value == 2 + random_int


@pytest.mark.asyncio(scope="session")
async def test_cache_invalidation(random_int: int, salt: str):

    @cached(5, cache_key_salt=salt)
    async def plus_random(x):
        return x + random_int

    _ = await plus_random(x=2)
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name=plus_random.__name__, cache_key_salt=salt, x=2)
    assert await redis.get(key)

    await invalidate_cache(func_name=plus_random.__name__, cache_key_salt=salt, x=2)
    assert not await redis.get(key)


class TestModel(BaseModel):
    x: int
    dt: datetime.datetime


@pytest.mark.asyncio(scope="session")
async def test_pydantic_serialization(random_int: int, salt: str):

    @cached(5, cache_key_salt=salt)
    async def plus_random(obj: TestModel) -> TestModel:
        obj.x += random_int
        return obj

    dt = datetime.datetime.now()
    obj = await plus_random(obj=TestModel(x=2, dt=dt))
    assert obj.x == 2 + random_int

    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='plus_random', cache_key_salt=salt, obj=TestModel(x=2, dt=dt))
    value = await redis.get(key)
    assert isinstance(value, TestModel)
    assert value.x == 2 + random_int
    assert isinstance(value.dt, datetime.datetime)

    obj = await plus_random(obj=TestModel(x=2, dt=dt))
    assert isinstance(obj, TestModel)
    assert obj.x == 2 + random_int
    assert isinstance(obj.dt, datetime.datetime)

    another_x = 5
    obj = await plus_random(obj=TestModel(x=another_x, dt=dt))
    assert obj.x == another_x + random_int
