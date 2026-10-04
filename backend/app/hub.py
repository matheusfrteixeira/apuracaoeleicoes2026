"""WebSocket hub: empurra para cada cliente so o que ele esta olhando (cargo + escopo)."""
import asyncio
import logging

import orjson

from .config import settings
from .domain import CARGOS, UF_NAME

log = logging.getLogger("hub")
RN = f"uf:{settings.uf}"


class Conn:
    __slots__ = ("ws", "cargo", "scope")

    def __init__(self, ws):
        self.ws, self.cargo, self.scope = ws, "1", RN


def _msg(t: str, cargo: str | None, scope: str | None, blob: bytes, key="data") -> str:
    head = b'{"t":"%s"' % t.encode()
    if cargo:
        head += b',"cargo":"%s"' % cargo.encode()
    if scope:
        head += b',"scope":"%s"' % scope.encode()
    return (head + b',"%s":' % key.encode() + blob + b"}").decode()


class Hub:
    def __init__(self, store, info):
        self.store, self.info = store, info
        self.conns: set[Conn] = set()

    # ---------- helpers
    async def _blob(self, cache, key, last=False):
        if key in cache:
            return cache[key]
        v = await (self.store.llast(key) if last else self.store.get(key))
        cache[key] = v
        return v

    async def _hist_msgs(self, cache, cargo, scope, full):
        key = f"hist:{cargo}:{scope}"
        if full:
            pts = await self.store.lrange(key)
            return [_msg("hist", cargo, scope, b"[" + b",".join(pts) + b"]")]
        p = await self._blob(cache, key, last=True)
        return [_msg("hist_point", cargo, scope, p, key="point")] if p else []

    async def _push(self, conn, msgs):
        try:
            for m in msgs:
                await conn.ws.send_text(m)
        except Exception:  # noqa: BLE001
            self.conns.discard(conn)

    # ---------- snapshot (ao conectar / mudar de selecao)
    async def snapshot(self, conn, with_meta=False):
        cache, msgs = {}, []
        if with_meta:
            msgs.append(_msg("meta", None, None, orjson.dumps(self.meta())))
            nat = await self._blob(cache, "res:1:br")
            if nat:
                msgs.append(_msg("national", "1", "br", nat))
            msgs += await self._hist_msgs(cache, "1", "br", True)
        m = await self._blob(cache, f"map:{conn.cargo}")
        if m:
            msgs.append(_msg("map", conn.cargo, None, m))
        r = await self._blob(cache, f"res:{conn.cargo}:{conn.scope}")
        if r:
            msgs.append(_msg("result", conn.cargo, conn.scope, r))
        msgs += await self._hist_msgs(cache, conn.cargo, RN, True)
        await self._push(conn, msgs)

    def meta(self):
        return {
            "uf": settings.uf, "uf_nome": UF_NAME[settings.uf], "mode": settings.data_mode,
            "store": self.store.kind, "scope": RN,
            "cargos": [{"code": c["code"], "nome": c["nome"], "tipo": c["tipo"], "vagas": c["vagas"]} for c in CARGOS.values()],
        }

    # ---------- conexao
    async def handle(self, ws):
        await ws.accept()
        conn = Conn(ws)
        self.conns.add(conn)
        try:
            await self.snapshot(conn, with_meta=True)
            while True:
                msg = orjson.loads(await ws.receive_text())
                if msg.get("op") == "sub":
                    c = str(msg.get("cargo", conn.cargo))
                    s = str(msg.get("scope", conn.scope))
                    if c in CARGOS and (s == "br" or s.startswith(("uf:", "mun:"))):
                        conn.cargo, conn.scope = c, s
                        await self.snapshot(conn)
        except Exception:  # noqa: BLE001
            pass
        finally:
            self.conns.discard(conn)

    # ---------- eventos do ingestor
    async def run(self):
        async for raw in self.store.subscribe():
            try:
                ev = orjson.loads(raw)
                if ev.get("type") == "tick":
                    await self.on_tick(ev["cargo"])
            except Exception:  # noqa: BLE001
                log.exception("erro ao propagar tick")

    async def on_tick(self, cargo):
        cache: dict = {}
        jobs = []
        for conn in list(self.conns):
            msgs = []
            if conn.cargo == cargo:
                m = await self._blob(cache, f"map:{cargo}")
                r = await self._blob(cache, f"res:{cargo}:{conn.scope}")
                if m:
                    msgs.append(_msg("map", cargo, None, m))
                if r:
                    msgs.append(_msg("result", cargo, conn.scope, r))
                msgs += await self._hist_msgs(cache, cargo, RN, False)
            if cargo == "1":
                nat = await self._blob(cache, "res:1:br")
                if nat:
                    msgs.append(_msg("national", "1", "br", nat))
                msgs += await self._hist_msgs(cache, "1", "br", False)
            if msgs:
                jobs.append(self._push(conn, msgs))
        if jobs:
            await asyncio.gather(*jobs)
