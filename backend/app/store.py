"""Store com a mesma API para Redis (producao) e memoria (dev/testes)."""
import asyncio

from .config import settings

CHANNEL = "apuracao:events"


class MemoryStore:
    kind = "memory"

    def __init__(self):
        self.kv: dict = {}
        self.lists: dict = {}
        self.subs: list = []

    async def mset(self, d: dict):
        self.kv.update(d)

    async def get(self, k):
        return self.kv.get(k)

    async def rpush(self, k, v, cap):
        lst = self.lists.setdefault(k, [])
        lst.append(v)
        if len(lst) > cap:
            del lst[: len(lst) - cap]

    async def lrange(self, k, a=0, b=-1):
        lst = self.lists.get(k, [])
        return lst[a:] if b == -1 else lst[a: b + 1] if b >= 0 else lst[a:]

    async def llast(self, k):
        lst = self.lists.get(k, [])
        return lst[-1] if lst else None

    async def publish(self, msg: bytes):
        for q in list(self.subs):
            q.put_nowait(msg)

    async def subscribe(self):
        q: asyncio.Queue = asyncio.Queue()
        self.subs.append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self.subs.remove(q)


class RedisStore:
    kind = "redis"

    def __init__(self, url):
        import redis.asyncio as aioredis
        self.r = aioredis.from_url(url, decode_responses=False)

    async def mset(self, d: dict):
        if d:
            pipe = self.r.pipeline(transaction=False)
            pipe.mset(d)
            await pipe.execute()

    async def get(self, k):
        return await self.r.get(k)

    async def rpush(self, k, v, cap):
        pipe = self.r.pipeline(transaction=False)
        pipe.rpush(k, v)
        pipe.ltrim(k, -cap, -1)
        await pipe.execute()

    async def lrange(self, k, a=0, b=-1):
        return await self.r.lrange(k, a, b)

    async def llast(self, k):
        r = await self.r.lrange(k, -1, -1)
        return r[0] if r else None

    async def publish(self, msg: bytes):
        await self.r.publish(CHANNEL, msg)

    async def subscribe(self):
        ps = self.r.pubsub()
        await ps.subscribe(CHANNEL)
        try:
            async for m in ps.listen():
                if m["type"] == "message":
                    yield m["data"]
        finally:
            await ps.close()


def make_store():
    return RedisStore(settings.redis_url) if settings.redis_url else MemoryStore()
