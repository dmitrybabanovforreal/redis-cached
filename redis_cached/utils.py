import asyncio

from redis.asyncio.lock import Lock
from redis.exceptions import LockNotOwnedError, LockError


async def lock_release_retry(lock: Lock) -> bool:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await lock.release()
            return True
        except LockNotOwnedError:
            await asyncio.sleep(0.1)
        except LockError as e:
            if 'Cannot release an unlocked lock' in str(e):
                return True
            raise e
    return False
