"""
Fonte real: JSON do TSE (simulado ou oficial).

  br : {base}/br/br-c{cargo:04d}-e{ele:06d}-u.json
  uf : {base}/{uf}/{uf}-c{cargo:04d}-e{ele:06d}-u.json
  mun: {base}/{uf}/{uf}{cod_tse}-c{cargo:04d}-e{ele:06d}-u.json   (cod_tse != cod IBGE!)

O codigo do municipio no TSE nao e o do IBGE; descobrimos o mapeamento lendo o arquivo
de configuracao (config/mun-e{ele}-cm.json) e casando por NOME normalizado.
"""
import asyncio
import logging
import re
import unicodedata

import httpx

from .config import settings
from .domain import CARGOS, UFS
from .pipeline import make_result

log = logging.getLogger("tse")


def _i(x):
    try:
        return int(str(x).replace(".", "") or 0)
    except ValueError:
        return 0


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def parse_tse(payload: dict, scope: str, nome: str, cargo: str):
    carg = next((c for c in payload.get("carg", []) if str(c.get("cd")) == cargo), None) or (payload.get("carg") or [None])[0]
    if not carg:
        return None
    cands = []
    for agr in carg.get("agr", []):
        for par in agr.get("par", []):
            for c in par.get("cand", []):
                cands.append({
                    "id": str(c.get("sqcand")), "num": str(c.get("n", "")),
                    "nome": c.get("nmu") or c.get("nm") or "", "partido": par.get("sg", ""),
                    "votos": _i(c.get("vap")), "eleito": c.get("st") == "Eleito", "status": c.get("st", ""),
                })
    s, e, v = payload.get("s", {}), payload.get("e", {}), payload.get("v", {})
    return make_result(
        scope, cargo, nome, _i(s.get("ts")), _i(s.get("st")), _i(e.get("te")), _i(e.get("c")), _i(e.get("a")),
        _i(v.get("vb")), _i(v.get("tvn") or v.get("vn")), cands, f"{payload.get('dg', '')} {payload.get('hg', '')}".strip(),
    )


class TseSource:
    def __init__(self, municipios):
        self.municipios = municipios
        self.tse_code: dict = {}
        self.cache: dict = {}  # url -> (etag, parsed)
        self.client = None
        self.sem = asyncio.Semaphore(settings.tse_concurrency)

    def _ele_for_cargo(self, cargo: str) -> str:
        return settings.tse_ele_fed if str(cargo) == "1" else settings.tse_ele_est

    def _base_for_ele(self, ele: str) -> str:
        if "/ele" in settings.tse_base:
            prefix = settings.tse_base.rsplit("/ele", 1)[0]
            part = settings.tse_base[len(prefix):].lstrip("/").split("/")[0]
            return f"{prefix}/{part}/{ele}/dados"
        return settings.tse_base

    def _url(self, cargo, scope):
        ele_num = self._ele_for_cargo(cargo)
        ele = f"{int(ele_num):06d}"
        b = self._base_for_ele(ele_num)
        c = f"c{int(cargo):04d}-e{ele}-u.json"
        uf = settings.uf.lower()
        if scope == "br":
            return f"{b}/br/br-{c}"
        kind, key = scope.split(":")
        if kind == "uf":
            return f"{b}/{key.lower()}/{key.lower()}-{c}"
        return f"{b}/{uf}/{uf}{self.tse_code[key]}-{c}"

    async def init(self):
        self.client = httpx.AsyncClient(timeout=20, follow_redirects=True, http2=False)
        if settings.tse_fetch_municipalities:
            ele_num = settings.tse_ele_fed
            ele = f"{int(ele_num):06d}"
            base_dir = self._base_for_ele(ele_num).rsplit("/dados", 1)[0]
            cfg = f"{base_dir}/config/mun-e{ele}-cm.json"
            try:
                r = await self.client.get(cfg)
                r.raise_for_status()
                self.tse_code = self._map_codes(r.json())
                log.info("mapeados %d/%d municipios IBGE->TSE", len(self.tse_code), len(self.municipios))
            except Exception as e:  # noqa: BLE001
                log.error("nao consegui ler %s (%s). Municipios ficarao sem dados.", cfg, e)
        else:
            log.info("busca individual de municipios desativada (TSE_FETCH_MUNICIPALITIES=false)")

    def _map_codes(self, cfg):
        uf = settings.uf.upper()
        abr_list = cfg.get("abr", []) if isinstance(cfg, dict) else []
        node = next((item for item in abr_list if str(item.get("cd", "")).upper() == uf), None)
        if not node:
            def find(o):
                nonlocal node
                if node is not None:
                    return
                if isinstance(o, dict):
                    if str(o.get("cd", "")).upper() == uf:
                        node = o
                        return
                    for v in o.values():
                        find(v)
                elif isinstance(o, list):
                    for v in o:
                        find(v)
            find(cfg)

        by_ibge = {}
        by_name = {}
        if node and "mu" in node:
            for m in node["mu"]:
                cd = str(m.get("cd", "")).zfill(5)
                cdi = str(m.get("cdi", "")).strip()
                nm = m.get("nm") or m.get("ds")
                if cdi:
                    by_ibge[cdi] = cd
                if nm:
                    by_name[norm(nm)] = cd
        else:
            def walk(o):
                if isinstance(o, dict):
                    cd, nm, cdi = str(o.get("cd", "")), o.get("nm") or o.get("ds"), str(o.get("cdi", "")).strip()
                    if re.fullmatch(r"\d{4,5}", cd):
                        zcd = cd.zfill(5)
                        if cdi:
                            by_ibge[cdi] = zcd
                        if nm:
                            by_name[norm(nm)] = zcd
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(node if node is not None else cfg)

        mapped = {}
        for m in self.municipios:
            mid = str(m["id"])
            if mid in by_ibge:
                mapped[mid] = by_ibge[mid]
            elif norm(m["nome"]) in by_name:
                mapped[mid] = by_name[norm(m["nome"])]
        return mapped

    async def _one(self, cargo, scope, nome):
        url = self._url(cargo, scope)
        hdr = {}
        etag, parsed = self.cache.get(url, (None, None))
        if etag:
            hdr["If-None-Match"] = etag
        async with self.sem:
            try:
                r = await self.client.get(url, headers=hdr)
            except httpx.HTTPError as e:
                log.debug("falha %s: %s", url, e)
                return scope, parsed
        if r.status_code == 304:
            return scope, parsed
        if r.status_code != 200:
            return scope, parsed
        parsed = parse_tse(r.json(), scope, nome, cargo)
        self.cache[url] = (r.headers.get("etag"), parsed)
        return scope, parsed

    async def fetch(self):
        out = {}
        for cargo, meta in CARGOS.items():
            jobs = [self._one(cargo, f"uf:{settings.uf}", settings.uf)]
            if meta["national"]:
                jobs.append(self._one(cargo, "br", "Brasil"))
                if settings.tse_fetch_other_ufs:
                    jobs += [self._one(cargo, f"uf:{sg}", nm) for sg, nm, _ in UFS if sg != settings.uf]
            if settings.tse_fetch_municipalities:
                jobs += [self._one(cargo, f"mun:{m['id']}", m["nome"]) for m in self.municipios if m["id"] in self.tse_code]
            res = await asyncio.gather(*jobs)
            out[cargo] = {s: r for s, r in res if r}
        return out
