from typing import Any
import pickle, os

from redis.asyncio.client import Redis


class KeyNotFound(Exception):
    pass


class Redis_(Redis):
    async def get_(self, name: str) -> Any:
        res = await self.get(name)
        if not res:
            raise KeyNotFound()
        return pickle.loads(res)

    async def set_(self,
        name: str,
        value: Any,
        ex: None | int = None,
        px: None | int = None,
        nx: bool = None,
        xx: bool = None,
        keepttl: bool = None,
        get: bool = None,
        exat: Any | None = None,
        pxat: Any | None = None) -> Any:
        value = pickle.dumps(value)
        return await self.set(
            name=name,
            value=value,
            ex=ex,
            px=px,
            nx=nx,
            xx=xx,
            keepttl=keepttl,
            get=get,
            exat=exat,
            pxat=pxat
        )


host = os.getenv('REDIS_CACHED_HOST')
assert host

redis = Redis_(
    host=host,
    port=int(os.getenv('REDIS_CACHED_PORT') or 6379),
    db=int(os.getenv('REDIS_CACHED_DB') or 0),
)
