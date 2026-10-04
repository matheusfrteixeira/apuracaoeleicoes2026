"""Normaliza -> agrega -> projeta -> monta os payloads que vao para o Redis/WebSocket."""
from .config import settings
from .domain import CARGOS, UF_NAME
from .forecast import forecast, unit_projection


def make_result(scope, cargo, nome, secoes_total, secoes_ap, eleitores, comparecimento,
                abstencao, brancos, nulos, cands, gerado=None):
    cands = sorted(cands, key=lambda c: c["votos"], reverse=True)
    validos = sum(c["votos"] for c in cands)
    for c in cands:
        c["pct"] = round(c["votos"] / validos * 100, 3) if validos else 0.0
    return {
        "scope": scope, "cargo": cargo, "nome": nome, "gerado": gerado,
        "apuracao": {
            "total": secoes_total, "apuradas": secoes_ap,
            "pct": round(secoes_ap / secoes_total * 100, 2) if secoes_total else 0.0,
        },
        "eleitorado": {"total": eleitores, "comparecimento": comparecimento, "abstencao": abstencao},
        "votos": {"validos": validos, "brancos": brancos, "nulos": nulos, "total": validos + brancos + nulos},
        "cand": cands,
    }


def aggregate(scope, cargo, nome, children):
    acc: dict = {}
    for ch in children:
        for c in ch["cand"]:
            a = acc.get(c["id"])
            if a is None:
                a = acc[c["id"]] = {**c, "votos": 0}
            a["votos"] += c["votos"]
    sm = lambda f: sum(f(ch) for ch in children)  # noqa: E731
    return make_result(
        scope, cargo, nome,
        sm(lambda c: c["apuracao"]["total"]), sm(lambda c: c["apuracao"]["apuradas"]),
        sm(lambda c: c["eleitorado"]["total"]), sm(lambda c: c["eleitorado"]["comparecimento"]),
        sm(lambda c: c["eleitorado"]["abstencao"]),
        sm(lambda c: c["votos"]["brancos"]), sm(lambda c: c["votos"]["nulos"]),
        list(acc.values()),
    )


def _shares(res):
    v = sum(c["votos"] for c in res["cand"])
    return {c["id"]: (c["votos"] / v if v else 0.0) for c in res["cand"]}


def _trim(res, n):
    out = {**res, "cand": res["cand"][:n]}
    out["outros"] = sum(c["votos"] for c in res["cand"][n:])
    return out


def build_cargo(cargo: str, units: dict, ts: float) -> dict:
    """units: {'mun:2400109': res, 'uf:SP': res, 'uf:RN': res?, 'br': res?}"""
    meta = CARGOS[cargo]
    uf = settings.uf
    rn = f"uf:{uf}"
    muns = {s: r for s, r in units.items() if s.startswith("mun:")}
    if rn not in units and muns:
        units[rn] = aggregate(rn, cargo, UF_NAME[uf], list(muns.values()))
    ufs = {s: r for s, r in units.items() if s.startswith("uf:")}
    if meta["national"] and "br" not in units and ufs:
        units["br"] = aggregate("br", cargo, "Brasil", list(ufs.values()))
    if not units:
        return {}

    prior_rn = _shares(units[rn]) if rn in units else {}
    prior_br = _shares(units["br"]) if "br" in units else prior_rn

    up = {s: unit_projection(r, prior_rn) for s, r in muns.items()}
    for s, r in ufs.items():
        if s != rn:
            up[s] = unit_projection(r, prior_br)
    rn_units = list(up[s] for s in muns) or ([unit_projection(units[rn], prior_br)] if rn in units else [])

    fc = {}
    for s in muns:
        fc[s] = forecast([up[s]], meta)
    if rn in units:
        fc[rn] = forecast(rn_units, meta, with_p2t=True)
    for s in ufs:
        if s != rn:
            fc[s] = forecast([up[s]], meta)
    if "br" in units:
        fc["br"] = forecast([up[s] for s in ufs if s != rn] + rn_units, meta, with_p2t=True)

    # ---- payloads por escopo
    results = {}
    for s, r in units.items():
        n = 10 if s.startswith("mun:") else (40 if (s == rn and meta["tipo"] == "proporcional") else 12)
        out = _trim(r, n)
        out["forecast"] = fc.get(s)
        results[s] = out

    cand_info = {}
    for r in units.values():
        for c in r["cand"][:12]:
            cand_info.setdefault(c["id"], {"n": c["nome"], "p": c["partido"], "num": c["num"]})
    if rn in units:
        for c in units[rn]["cand"]:
            cand_info.setdefault(c["id"], {"n": c["nome"], "p": c["partido"], "num": c["num"]})

    if "br" in units:
        by_uf = []
        for s, r in sorted(ufs.items()):
            lead = r["cand"][0] if r["cand"] and r["cand"][0]["votos"] > 0 else None
            by_uf.append({
                "uf": s[3:], "nome": r["nome"], "w": lead["id"] if lead else None,
                "wp": lead["pct"] if lead else 0, "f": r["apuracao"]["pct"],
                "pj": (fc.get(s) or {}).get("lider") if s != rn else (fc.get(rn) or {}).get("lider"),
            })
        results["br"]["by_uf"] = by_uf

    items = []
    for s, r in muns.items():
        c = r["cand"]
        lead = c[0] if c and c[0]["votos"] > 0 else None
        sec = c[1] if len(c) > 1 and c[1]["votos"] > 0 else None
        f_ = fc[s]
        pj = f_["proj"][0] if f_["proj"] else None
        top_cands = [
            {"id": x["id"], "n": x["nome"], "p": x.get("partido", ""), "v": x["votos"], "pct": x["pct"]}
            for x in c[:4]
        ]
        items.append({
            "m": s[4:], "n": r["nome"],
            "w": lead["id"] if lead else None, "wp": lead["pct"] if lead else 0, "wv": lead["votos"] if lead else 0,
            "s": sec["id"] if sec else None, "sp": sec["pct"] if sec else 0, "sv": sec["votos"] if sec else 0,
            "f": r["apuracao"]["pct"], "v": r["votos"]["validos"], "e": r["eleitorado"]["total"],
            "pj": pj["id"] if pj else None, "pjp": pj["pct"] if pj else 0,
            "pw": (f_["prob"].get(pj["id"]) if (pj and f_["prob"]) else None),
            "top": top_cands,
        })
        for k in ("w", "s", "pj"):
            cid = items[-1][k]
            if cid and cid not in cand_info:
                cand_info[cid] = {"n": next((x["nome"] for x in c if x["id"] == cid), cid),
                                  "p": next((x["partido"] for x in c if x["id"] == cid), ""), "num": ""}
    items.sort(key=lambda i: i["n"])
    legend = [c["id"] for c in units[rn]["cand"][:12]] if rn in units else []
    map_payload = {"cargo": cargo, "ts": ts, "legend": legend, "cands": cand_info, "items": items}

    # ---- historico (so br e UF)
    hist = {}
    for s in (rn, "br"):
        if s in units and fc.get(s) and fc[s]["proj"]:
            top = fc[s]["proj"][:6]
            cur = {c["id"]: c["pct"] for c in units[s]["cand"]}
            hist[s] = {
                "t": ts, "f": units[s]["apuracao"]["pct"],
                "p": {x["id"]: x["pct"] for x in top},
                "c": {x["id"]: cur.get(x["id"], 0) for x in top},
            }
    return {"results": results, "map": map_payload, "hist": hist}
