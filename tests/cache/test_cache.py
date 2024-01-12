import asyncio, datetime, time

import pytest
from pydantic import BaseModel

from redis_cached.redis import redis, KeyNotFound
from redis_cached.core import _get_cache_key
from redis_cached import cached, invalidate_cache
from tests.utils import random_string


@pytest.mark.asyncio(scope="session")
async def test_redis_connection():
    key = random_string()
    data = random_string()
    await redis.set_(key, data)
    assert await redis.get_(key) == data


@pytest.mark.asyncio(scope="session")
async def test_cache(random_int: int):

    @cached(1)
    async def plus_random(x):
        return x + random_int

    result = await plus_random(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='plus_random', cache_key_salt='', x=2)
    value = await redis.get_(key)
    assert value == 2 + random_int

    assert await plus_random(x=2) == 2 + random_int

    doctored_value = random_string()
    await redis.set_(key, doctored_value, ex=1)

    cached_result = await plus_random(x=2)
    assert cached_result == doctored_value


@pytest.mark.asyncio(scope="session")
async def test_cache_none_value():

    @cached(1)
    async def return_none(x):
        return None

    result = await return_none(x=2)
    assert result is None
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='return_none', cache_key_salt='', x=2)
    assert await redis.exists(key) == 1
    value = await redis.get_(key)
    assert value is None

    assert await return_none(x=2) is None

    doctored_value = random_string()
    await redis.set_(key, doctored_value, ex=1)

    cached_result = await return_none(x=2)
    assert cached_result == doctored_value


@pytest.mark.asyncio(scope="session")
async def test_cache_with_salt(random_int: int, salt: str):

    @cached(1, cache_key_salt=salt)
    async def plus_random(x):
        return x + random_int

    result = await plus_random(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='plus_random', cache_key_salt=salt, x=2)
    value = await redis.get_(key)
    assert value == 2 + random_int


@pytest.mark.asyncio(scope="session")
async def test_cache_invalidation(random_int: int, salt: str):

    @cached(1, cache_key_salt=salt)
    async def plus_random(x):
        return x + random_int

    _ = await plus_random(x=2)
    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name=plus_random.__name__, cache_key_salt=salt, x=2)
    assert await redis.get_(key)

    await invalidate_cache(func_name=plus_random.__name__, cache_key_salt=salt, x=2)
    with pytest.raises(KeyNotFound):
        await redis.get_(key)


class TestModel(BaseModel):
    x: int
    dt: datetime.datetime


@pytest.mark.asyncio(scope="session")
async def test_pydantic_serialization(random_int: int, salt: str):

    @cached(1, cache_key_salt=salt)
    async def plus_random(obj: TestModel) -> TestModel:
        obj.x += random_int
        return obj

    dt = datetime.datetime.now()
    obj = await plus_random(obj=TestModel(x=2, dt=dt))
    assert obj.x == 2 + random_int

    await asyncio.sleep(0.01)  # let it write to the db

    key = _get_cache_key(func_name='plus_random', cache_key_salt=salt, obj=TestModel(x=2, dt=dt))
    value = await redis.get_(key)
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


@pytest.mark.asyncio(scope="session")
async def test_simultaneous_cache_misses():
    # Tests that in situation of simultaneous cache misses
    # (e.g. from concurrent calls with the same arguments),
    # only the first call takes care of executing the
    # function and updating the cached value.

    calls = {'count': 0}

    @cached(1)
    async def expensive_io_task(x) -> float:
        calls['count'] += 1
        await asyncio.sleep(0.1)
        return time.time()

    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(expensive_io_task(x=2))
        await asyncio.sleep(0.01)
        task2 = tg.create_task(expensive_io_task(x=2))
        await asyncio.sleep(0.01)
        task3 = tg.create_task(expensive_io_task(x=2))
        other_task = tg.create_task(expensive_io_task(x=3))

    assert task1.result() == task2.result() == task3.result()
    assert other_task.result() > task1.result()

    assert calls['count'] == 2


@pytest.mark.asyncio(scope="session")
async def test_async_func_validation_at_definition_time():
    with pytest.raises(AssertionError) as exc_info:
        @cached(5)
        def my_func():
            pass
    assert 'Only async functions are supported' in str(exc_info.value)
