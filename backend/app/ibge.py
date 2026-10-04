"""Municipios e malha (GeoJSON) do IBGE, com cache em disco."""
import json
import logging
import os

import httpx

from .config import settings

log = logging.getLogger("ibge")


def _cache(name):
    os.makedirs(settings.data_dir, exist_ok=True)
    return os.path.join(settings.data_dir, f"{name}_{settings.uf}.json")


async def _get(url):
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


async def load_municipios() -> list:
    path = _cache("municipios")
    try:
        raw = await _get(settings.ibge_muns.format(ibge=settings.uf_ibge))
        data = [{"id": str(m["id"]), "nome": m["nome"]} for m in json.loads(raw)]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data
    except Exception as e:  # noqa: BLE001
        log.warning("IBGE municipios indisponivel (%s); tentando cache", e)
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    log.warning("sem cache: gerando 167 municipios sinteticos")
    base = settings.uf_ibge * 100000
    return [{"id": str(base + i * 10), "nome": f"Município {i + 1:03d}"} for i in range(167)]


def _ring_area(coords):
    return sum(coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1] for i in range(len(coords) - 1)) / 2.0


def _rewind_ring(ring, should_be_negative: bool):
    a = _ring_area(ring)
    if (a > 0 and should_be_negative) or (a < 0 and not should_be_negative):
        return ring[::-1]
    return ring


def _rewind_geom(geom):
    gt = geom.get("type")
    coords = geom.get("coordinates", [])
    if gt == "Polygon":
        geom["coordinates"] = [_rewind_ring(r, i == 0) for i, r in enumerate(coords)]
    elif gt == "MultiPolygon":
        geom["coordinates"] = [[_rewind_ring(r, i == 0) for i, r in enumerate(poly)] for poly in coords]
    return geom


def _normalize_geo(raw: bytes) -> bytes:
    try:
        data = json.loads(raw)
        for feat in data.get("features", []):
            if "geometry" in feat and feat["geometry"]:
                _rewind_geom(feat["geometry"])
        return json.dumps(data, ensure_ascii=False).encode("utf-8")
    except Exception as e:
        log.warning("Falha ao normalizar GeoJSON: %s", e)
        return raw


async def load_geo() -> bytes | None:
    path = _cache("geo")
    # Se ja existe cache em disco, tenta usa-lo
    if os.path.exists(path):
        try:
            cached = open(path, "rb").read()
            return _normalize_geo(cached)
        except Exception:
            pass
    try:
        raw = await _get(settings.ibge_geo.format(uf=settings.uf))
        normalized = _normalize_geo(raw)
        with open(path, "wb") as f:
            f.write(normalized)
        return normalized
    except Exception as e:  # noqa: BLE001
        log.warning("IBGE malha indisponivel (%s); tentando cache", e)
    return open(path, "rb").read() if os.path.exists(path) else None

