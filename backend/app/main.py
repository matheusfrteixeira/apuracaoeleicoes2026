import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import ibge
from .config import settings
from .domain import CARGOS
from .hub import Hub
from .ingest import Ingestor
from .mock import MockSource
from .store import make_store
from .tse import TseSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
JSON = "application/json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = make_store()
    hub = Hub(store, {})
    app.state.store, app.state.hub = store, hub
    app.state.municipios = await ibge.load_municipios()
    app.state.geo = await ibge.load_geo()
    tasks = [asyncio.create_task(hub.run())]
    if settings.embedded:
        src = MockSource(app.state.municipios) if settings.data_mode == "mock" else TseSource(app.state.municipios)
        app.state.ingestor = Ingestor(store, src)
        tasks.append(asyncio.create_task(app.state.ingestor.run()))
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="Apuracao 2026", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.get("/api/health")
async def health():
    ing = getattr(app.state, "ingestor", None)
    return {"ok": True, "mode": settings.data_mode, "store": app.state.store.kind,
            "ticks": ing.ticks if ing else None, "last_tick": ing.last_ts if ing else None,
            "municipios": len(app.state.municipios), "geo": app.state.geo is not None}


@app.get("/api/meta")
async def meta():
    return app.state.hub.meta()


@app.get("/api/municipios")
async def municipios():
    return app.state.municipios


@app.get("/api/geo")
async def geo():
    if not app.state.geo:
        app.state.geo = await ibge.load_geo()
    if not app.state.geo:
        raise HTTPException(502, "Malha do IBGE indisponivel")
    return Response(app.state.geo, media_type=JSON, headers={"Cache-Control": "public, max-age=86400"})


# Os blobs ja estao serializados no Redis: devolvemos os bytes direto (sem decode/encode).
@app.get("/api/map/{cargo}")
async def get_map(cargo: str):
    if cargo not in CARGOS:
        raise HTTPException(404, "cargo invalido")
    b = await app.state.store.get(f"map:{cargo}")
    if not b:
        raise HTTPException(503, "apuracao ainda nao iniciada")
    return Response(b, media_type=JSON)


@app.get("/api/results/{cargo}/{scope:path}")
async def get_result(cargo: str, scope: str):
    b = await app.state.store.get(f"res:{cargo}:{scope}")
    if not b:
        raise HTTPException(404, "sem resultado para este escopo")
    return Response(b, media_type=JSON)


@app.get("/api/history/{cargo}/{scope:path}")
async def get_history(cargo: str, scope: str):
    pts = await app.state.store.lrange(f"hist:{cargo}:{scope}")
    return Response(b"[" + b",".join(pts) + b"]", media_type=JSON)


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await app.state.hub.handle(websocket)
