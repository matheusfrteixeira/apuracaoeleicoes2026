"""
Projecao de resultado final.

Ideia (simples e explicavel, boa para um MVP):
  * cada unidade (municipio ou UF) tem votos apurados V e fracao apurada f (secoes);
  * total final esperado T = V / f  (se f < 5%, usa eleitorado * participacao tipica);
  * votos restantes R = T - V sao distribuidos conforme a participacao observada,
    suavizada por um "prior" (share do nivel acima) -> evita extremos com poucas urnas;
  * incerteza = ruido multinomial sobre R  +  erro sistematico na participacao dos votos
    restantes (a ordem de apuracao NAO e aleatoria). O erro sistematico tem uma parte
    comum a todas as unidades (nao "some" na agregacao) e uma parte idiossincratica;
"""
from math import erf, sqrt

K_COMMON = 0.07              # vies sistematico COMPARTILHADO (ex.: urnas urbanas primeiro)
K_IDIO = 0.20                # vies proprio de cada unidade (municipio/UF)
PRIOR_W = 3000.0              # "votos fantasmas" do prior
TURNOUT_VALID = 0.80 * 0.92   # votos validos / eleitorado (so para f muito baixa)


def _phi(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def unit_projection(res: dict, prior: dict) -> dict:
    cands = res["cand"]
    votes = {c["id"]: c["votos"] for c in cands}
    V = float(sum(votes.values()))
    f = res["apuracao"]["pct"] / 100.0
    el = res["eleitorado"]["total"] or 0
    if f >= 0.05 and V > 0:
        T = V / f
    else:
        T = max(el * TURNOUT_VALID, V)
    R = max(T - V, 0.0)
    ids = set(votes) | set(prior)
    p = {cid: (votes.get(cid, 0.0) + PRIOR_W * prior.get(cid, 0.0)) / (V + PRIOR_W) if (V + PRIOR_W) else 0.0 for cid in ids}
    proj = {cid: votes.get(cid, 0.0) + R * p[cid] for cid in ids}
    return {"proj": proj, "R": R, "p": p, "V": V, "T": T}


def _var(units, i, j=None):
    """Variancia (em votos^2) do total de i, ou da diferenca i-j."""
    mult = common = idio = 0.0
    for u in units:
        pi = u["p"].get(i, 0.0)
        if j is None:
            s2 = pi * (1 - pi)
        else:
            pj = u["p"].get(j, 0.0)
            s2 = max(pi + pj - (pi - pj) ** 2, 0.0)
        a = u["R"] * sqrt(s2)
        mult += u["R"] * s2
        common += a
        idio += a * a
    return mult + (K_COMMON * common) ** 2 + (K_IDIO ** 2) * idio


def _pwin(mean: float, var: float) -> float:
    if var <= 1e-9:
        return 1.0 if mean > 0 else (0.5 if mean == 0 else 0.0)
    return _phi(mean / sqrt(var))


def forecast(units: list, meta: dict, with_p2t: bool = False) -> dict:
    tot: dict = {}
    for u in units:
        for cid, v in u["proj"].items():
            tot[cid] = tot.get(cid, 0.0) + v
    T = sum(tot.values())
    if T <= 0:
        return {"proj": [], "lider": None, "prob": {}, "p2t": None, "completude": 0.0}

    sumV = sum(u["V"] for u in units)
    sumT = sum(u["T"] for u in units)
    order = sorted(tot, key=tot.get, reverse=True)
    maj = meta["tipo"] == "majoritario"
    top = order[: 6 if maj else min(meta["vagas"] + 4, 30)]

    proj = []
    for cid in top:
        sd = sqrt(_var(units, cid)) / T * 100
        pct = tot[cid] / T * 100
        proj.append({
            "id": cid, "votos": round(tot[cid]), "pct": round(pct, 2),
            "lo": round(max(pct - 1.96 * sd, 0), 2), "hi": round(min(pct + 1.96 * sd, 100), 2),
        })

    prob: dict = {}
    if maj and meta["vagas"] == 1 and len(order) > 1:
        c4 = order[:4]
        score = {}
        for i in c4:
            s = 1.0
            for j in c4:
                if i == j:
                    continue
                var = _var(units, i, j)
                s *= _pwin(tot[i] - tot[j], var)
            score[i] = s
        z = sum(score.values()) or 1.0
        prob = {cid: round(score[cid] / z, 4) for cid in c4}

    p2t = None
    if with_p2t and maj and meta["vagas"] == 1 and proj:
        lead = proj[0]
        sd = (lead["hi"] - lead["lo"]) / (2 * 1.96)
        if sd > 0:
            p2t = round(_phi((50.0 - lead["pct"]) / sd), 4)
        else:
            p2t = 1.0 if lead["pct"] <= 50 else 0.0

    return {
        "proj": proj, "lider": order[0], "prob": prob, "p2t": p2t,
        "completude": round(sumV / sumT, 4) if sumT else 0.0,
    }
