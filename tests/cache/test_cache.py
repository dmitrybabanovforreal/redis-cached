import asyncio, datetime, time, os

import pytest
from pydantic import BaseModel
from redis import Redis as SyncRedis
from redis.asyncio.client import Redis

from redis_cached.core import KeyNotFound, Cache
from tests.utils import random_string


@pytest.mark.asyncio(scope="session")
async def test_redis_connection():
    key = random_string()
    data = random_string()
    cache = Cache()
    await cache._redis_set(key, data)
    assert await cache._redis_get(key) == data


@pytest.mark.asyncio(scope="session")
async def test_cache(random_int: int):
    cache = Cache()

    @cache.cached(1)
    async def plus_random_1(x):
        return x + random_int

    result = await plus_random_1(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = cache._get_cache_key(func_name='plus_random_1', x=2)
    value = await cache._redis_get(key)
    assert value == 2 + random_int

    assert await plus_random_1(x=2) == 2 + random_int

    doctored_value = random_string()
    await cache._redis_set(key, doctored_value, ex=1)

    cached_result = await plus_random_1(x=2)
    assert cached_result == doctored_value


@pytest.mark.asyncio(scope="session")
async def test_cache_none_value():
    cache = Cache()

    @cache.cached(1)
    async def return_none(x):
        return None

    result = await return_none(x=2)
    assert result is None
    await asyncio.sleep(0.01)  # let it write to the db

    key = cache._get_cache_key(func_name='return_none', x=2)
    assert await cache.redis.exists(key) == 1
    value = await cache._redis_get(key)
    assert value is None

    assert await return_none(x=2) is None

    doctored_value = random_string()
    await cache._redis_set(key, doctored_value, ex=1)

    cached_result = await return_none(x=2)
    assert cached_result == doctored_value


@pytest.mark.asyncio(scope="session")
async def test_cache_with_salt(random_int: int, salt: str):
    cache = Cache(cache_key_salt=salt)

    @cache.cached(1)
    async def plus_random_2(x):
        return x + random_int

    result = await plus_random_2(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = cache._get_cache_key(func_name='plus_random_2', x=2)
    value = await cache._redis_get(key)
    assert value == 2 + random_int


@pytest.mark.asyncio(scope="session")
async def test_cache_invalidation(random_int: int, salt: str):
    cache = Cache(cache_key_salt=salt)

    @cache.cached(1)
    async def plus_random_3(x):
        return x + random_int

    _ = await plus_random_3(x=2)
    await asyncio.sleep(0.01)  # let it write to the db

    key = cache._get_cache_key(func_name=plus_random_3.__name__, x=2)
    assert await cache._redis_get(key)

    await cache.invalidate_cache(func_name=plus_random_3.__name__, x=2)
    with pytest.raises(KeyNotFound):
        await cache._redis_get(key)


class TestModel(BaseModel):
    x: int
    dt: datetime.datetime


@pytest.mark.asyncio(scope="session")
async def test_pydantic_serialization(random_int: int, salt: str):
    cache = Cache(cache_key_salt=salt)

    @cache.cached(1)
    async def plus_random_4(obj: TestModel) -> TestModel:
        obj.x += random_int
        return obj

    dt = datetime.datetime.now()
    obj = await plus_random_4(obj=TestModel(x=2, dt=dt))
    assert obj.x == 2 + random_int

    await asyncio.sleep(0.01)  # let it write to the db

    key = cache._get_cache_key(func_name='plus_random_4', obj=TestModel(x=2, dt=dt))
    value = await cache._redis_get(key)
    assert isinstance(value, TestModel)
    assert value.x == 2 + random_int
    assert isinstance(value.dt, datetime.datetime)

    obj = await plus_random_4(obj=TestModel(x=2, dt=dt))
    assert isinstance(obj, TestModel)
    assert obj.x == 2 + random_int
    assert isinstance(obj.dt, datetime.datetime)

    another_x = 5
    obj = await plus_random_4(obj=TestModel(x=another_x, dt=dt))
    assert obj.x == another_x + random_int


@pytest.mark.asyncio(scope="session")
async def test_simultaneous_cache_misses():
    # Tests that in situation of simultaneous cache misses
    # (e.g. from concurrent calls with the same arguments),
    # only the first call takes care of executing the
    # function and updating the cached value.

    calls = {'count': 0}
    cache = Cache()

    @cache.cached(1)
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
    cache = Cache()
    with pytest.raises(AssertionError) as exc_info:
        @cache.cached(5)
        def my_func():
            pass
    assert 'Only async functions are supported' in str(exc_info.value)


@pytest.mark.asyncio(scope="session")
async def test_redis_instance_validation():
    with pytest.raises(AssertionError) as exc_info:
        Cache(redis_=SyncRedis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT') or 6379),
            db=int(os.getenv('REDIS_DB') or 0),
        ))

    assert '`redis_` has to be an instance of redis.asyncio.client.Redis' in str(exc_info.value)


@pytest.mark.asyncio(scope="session")
async def test_cache_with_custom_redis(random_int: int):
    custom_redis = Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT') or 6379),
        db=int(os.getenv('REDIS_DB') or 0),
    )
    cache = Cache(redis_=custom_redis)

    @cache.cached(1)
    async def plus_random_5(x):
        return x + random_int

    result = await plus_random_5(x=2)
    assert result == 2 + random_int
    await asyncio.sleep(0.01)  # let it write to the db

    key = cache._get_cache_key(func_name='plus_random_5', x=2)
    value = await cache._redis_get(key)
    assert value == 2 + random_int

    assert await plus_random_5(x=2) == 2 + random_int

    doctored_value = random_string()
    await cache._redis_set(key, doctored_value, ex=1)

    cached_result = await plus_random_5(x=2)
    assert cached_result == doctored_value
