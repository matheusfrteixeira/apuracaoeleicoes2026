"""Valida o RedisStore (com fakeredis) + Ingestor + Hub: mesmo caminho de producao."""
import asyncio, sys, json
sys.path.insert(0, ".")
import fakeredis.aioredis as fr
from app import store as store_mod
from app.store import RedisStore
from app.ingest import Ingestor
from app.mock import MockSource
from app.hub import Hub

class FakeWS:
    def __init__(self): self.sent = []
    async def send_text(self, m): self.sent.append(json.loads(m))

async def main():
    import fakeredis; server = fakeredis.FakeServer()
    st = RedisStore.__new__(RedisStore); st.r = fr.FakeRedis(server=server, decode_responses=False)
    muns = [{"id": str(2400000 + i * 10), "nome": f"M{i}"} for i in range(167)]
    src = MockSource(muns); await src.init()
    hub = Hub(st, {})
    runner = asyncio.create_task(hub.run()); await asyncio.sleep(0.2)
    from app.hub import Conn
    ws = FakeWS(); c = Conn(ws); hub.conns.add(c)
    ing = Ingestor(st, src)
    for step in (0.2, 0.5):
        data = src.world.snapshot(step)
        for cargo, units in data.items(): await ing.process(cargo, units)
        await asyncio.sleep(0.3)
    kinds = {}
    for m in ws.sent: kinds[m["t"]] = kinds.get(m["t"], 0) + 1
    print("msgs recebidas via Redis pub/sub:", kinds)
    print("keys:", len(await st.r.keys("*")), "| hist len:", len(await st.lrange("hist:1:uf:RN")))
    await hub.snapshot(c, with_meta=True)
    print("snapshot ok:", sorted({m["t"] for m in ws.sent}))
    runner.cancel()
asyncio.run(main())
