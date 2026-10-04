import asyncio
import logging
import time

import orjson

from .config import settings
from .domain import CARGOS
from .pipeline import build_cargo

log = logging.getLogger("ingest")


class Ingestor:
    def __init__(self, store, source):
        self.store, self.source = store, source
        self.ticks = 0
        self.last_ts = 0.0

    async def process(self, cargo, units):
        ts = time.time()
        built = build_cargo(cargo, units, ts)
        if not built:
            return
        kv = {f"res:{cargo}:{s}": orjson.dumps(r) for s, r in built["results"].items()}
        kv[f"map:{cargo}"] = orjson.dumps(built["map"])
        await self.store.mset(kv)
        for s, p in built["hist"].items():
            await self.store.rpush(f"hist:{cargo}:{s}", orjson.dumps(p), settings.hist_cap)
        await self.store.publish(orjson.dumps({"type": "tick", "cargo": cargo, "ts": ts}))

    async def run(self):
        await self.source.init()
        while True:
            t0 = time.time()
            try:
                data = await self.source.fetch()
                for cargo, units in data.items():
                    await self.process(cargo, units)
                self.ticks += 1
                self.last_ts = time.time()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                log.exception("falha no ciclo de ingestao")
            wait = (settings.poll_seconds if settings.data_mode == "tse" else 2.0) - (time.time() - t0)
            await asyncio.sleep(max(wait, 0.2))
