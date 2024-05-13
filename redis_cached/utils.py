import asyncio

from redis.asyncio.lock import Lock
from redis.exceptions import LockNotOwnedError


async def lock_release_retry(lock: Lock) -> bool:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await lock.release()
            return True
        except LockNotOwnedError:
            await asyncio.sleep(0.1)
    return False
