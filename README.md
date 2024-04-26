# redis-cached
Python cache decorator that uses Redis or KeyDB as storage. This is very handy for replicated apps (e.g. Kubernetes), AWS Lambda functions, and other stateless apps.

Features:
* Function result and kwarg values are [pickled](https://docs.python.org/3/library/pickle.html), so you can work with complex structures like [pydantic](https://docs.pydantic.dev/latest/)'s `BaseModel`
* Prevents multiple simultaneous cache updates when a function is called concurrently and there is no cached value.
* Cache invalidation is available

Limitations:
* Only async functions are supported.
* Only keyword arguments are supported. It will raise an error if you pass non-kwargs while calling your function.

# Installation

```shell
pip install redis_cached
```

# Usage

Basic usage:

```python
import asyncio
from redis_cached import Cache

cache = Cache()

@cache.cached(5)
async def get_user_data(user_id: int):
    # expensive API call here
    return {'user_id': user_id, 'name': 'John Doe'}

async def main():
    user_data = await get_user_data(user_id=1)  # result is cached for 5 seconds
    
    # To invalidate the cache for the user with ID 1, pass the same kwargs:
    await cache.invalidate_cache('get_user_data', user_id=1)

asyncio.run(main())
```


Optionally, add salt to `cache_key_salt` to avoid clashing with the same-named functions in other modules or other apps that use the same Redis database.

You can also use your custom-configured async Redis instance with the cache.

```python
import asyncio
from redis.asyncio.client import Redis
from redis_cached import Cache

custom_redis = Redis(
    host='localhost',
    port=6379,
    db=0
)
cache = Cache(
    cache_key_salt='qhDwh9Y',
    redis_=custom_redis
)

@cache.cached(5)
async def get_user_data(user_id: int):
    # expensive API call here
    return {'user_id': user_id, 'name': 'John Doe'}

async def main():
    user_data = await get_user_data(user_id=1)  # cached
    await cache.invalidate_cache('get_user_data', user_id=1)  # invalidated

asyncio.run(main())
```

# Contributing

Contributions are welcome. Please refer to the [maintenance readme](./maintenance/README.md) for more details.
