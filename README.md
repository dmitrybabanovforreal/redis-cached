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
from redis_cached import cached, invalidate_cache

@cached(5)
async def add_one(x):
    return x + 1

async def main():
    result = await add_one(x=2)  # result is cached for 5 seconds
    
    # Pass the same kwargs to this func to invalidate the cache
    await invalidate_cache('add_one', x=2)

asyncio.run(main())
```


Optionally, add salt to the decorator to avoid clashing with the same-named functions in other modules or other apps that use the same Redis or KeyDB database:

```python
import asyncio
from redis_cached import cached, invalidate_cache

CACHE_SALT = 'XnsJ-7C9PIU0qhDwh9YhJQ'

@cached(5, cache_key_salt=CACHE_SALT)
async def add_one(x):
    return x + 1

async def invalidate_add_one(**kwargs):
    await invalidate_cache('add_one', cache_key_salt=CACHE_SALT, **kwargs)

async def main():
    result = await add_one(x=2)  # cached
    await invalidate_add_one(x=2)  # invalidated

asyncio.run(main())
```

# Contributing

Contributions are welcome. Please refer to [maintenance readme](./maintenance/README.md) for more details.
