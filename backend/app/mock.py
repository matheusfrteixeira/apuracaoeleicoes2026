"""
Simulador de apuracao (DATA_MODE=mock): gera resultados progressivos e plausiveis para
os 167 municipios do RN + 26 UFs (presidente), com vies de ordem de apuracao
(urnas urbanas chegam antes) para que a projecao tenha o que corrigir.
Dados 100% ficticios.
"""
import math
import random
import time

from .config import settings
from .domain import CARGOS, UFS
from .pipeline import make_result

FIRST = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fabio", "Giovana", "Heitor", "Iara", "Jonas", "Karina",
         "Lucas", "Marta", "Nilton", "Olga", "Paulo", "Rita", "Sergio", "Tereza", "Vitor", "Zeca", "Dayse"]
LAST = ["Alencar", "Bezerra", "Cabral", "Dantas", "Fernandes", "Galvão", "Holanda", "Medeiros", "Nogueira",
        "Pereira", "Queiroz", "Rocha", "Saldanha", "Tavares", "Vidal", "Maia", "Câmara", "Fonseca"]
PARTIES = ["PAU", "UCV", "RNV", "PDL", "FMS", "PSX", "MLB", "AVT", "PTN", "CDS", "PRO", "SLD"]

WEIGHTS = {
    "1": [0.33, 0.30, 0.15, 0.10, 0.07, 0.05],
    "3": [0.38, 0.30, 0.14, 0.10, 0.08],
    "5": [0.24, 0.20, 0.16, 0.14, 0.10, 0.09, 0.07],
}
N_PROP = {"6": 28, "7": 48}
BIG = {"2408102": 600_000, "2408003": 200_000, "2403251": 175_000, "2412005": 80_000,
       "2407104": 62_000, "2402600": 56_000}


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class MockWorld:
    def __init__(self, municipios: list, seed: int = 2026):
        rnd = random.Random(seed)
        self.muns = []
        for m in municipios:
            e = BIG.get(m["id"]) or int(rnd.lognormvariate(math.log(7000), 0.75))
            start = rnd.uniform(0, 0.2)
            dur = min(rnd.uniform(0.35, 0.8), 1 - start)
            self.muns.append({"id": m["id"], "nome": m["nome"], "E": max(e, 800), "urb": min(1.0, e / 60000) ** 0.5,
                              "start": start, "dur": dur})
        self.ufs = []
        for sg, nome, e in UFS:
            if sg == settings.uf:
                continue
            start = rnd.uniform(0, 0.2)
            self.ufs.append({"id": sg, "nome": nome, "E": e * 1000, "urb": rnd.random(),
                             "start": start, "dur": min(rnd.uniform(0.4, 0.8), 1 - start)})
        self.cands: dict = {}
        for cargo in CARGOS:
            n = N_PROP.get(cargo) or len(WEIGHTS[cargo])
            lst = []
            for i in range(n):
                w = WEIGHTS[cargo][i] if cargo in WEIGHTS else 1 / (i + 1) ** 0.9
                nome = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
                homes = set(rnd.sample([m["id"] for m in self.muns], rnd.randint(1, 3))) if cargo in N_PROP else set()
                lst.append({"id": f"{cargo}{i + 1:04d}", "num": str(10 + i * (3 if cargo in WEIGHTS else 1) + (0 if cargo in WEIGHTS else 100)),
                            "nome": nome, "partido": rnd.choice(PARTIES), "w": w,
                            "urb": rnd.uniform(-1, 1), "homes": homes})
            self.cands[cargo] = lst
        self.base: dict = {}
        self.bias: dict = {}
        for cargo in CARGOS:
            for u in self.muns:
                self._init(cargo, f"mun:{u['id']}", u, rnd, u["id"])
            if CARGOS[cargo]["national"]:
                for u in self.ufs:
                    self._init(cargo, f"uf:{u['id']}", u, rnd, None, sigma=0.4)

    def _init(self, cargo, key, u, rnd, mid, sigma=0.28):
        raw = []
        for c in self.cands[cargo]:
            x = c["w"] * math.exp(rnd.gauss(0, sigma) + c["urb"] * (u["urb"] - 0.5) * 1.2)
            if mid and mid in c["homes"]:
                x *= 9
            raw.append(x)
        s = sum(raw)
        self.base[(cargo, key)] = [x / s for x in raw]
        self.bias[(cargo, key)] = [rnd.gauss(0, 0.10) for _ in raw]

    def _unit(self, cargo, key, nome, u, t):
        f = _smooth((t - u["start"]) / u["dur"]) if u["dur"] > 0 else 1.0
        if t >= 1:
            f = 1.0
        E = u["E"]
        ts_ = max(3, E // 320)
        ap = round(ts_ * f)
        f = ap / ts_          # votos derivam das secoes apuradas (como no TSE)
        cands = self.cands[cargo]
        base, bias = self.base[(cargo, key)], self.bias[(cargo, key)]
        valid_total = E * 0.80 * 0.92
        counted = int(valid_total * f)
        adj = [max(b * (1 + bi * (1 - f) + c["urb"] * 0.25 * (1 - f)), 1e-9)
               for b, bi, c in zip(base, bias, cands)]
        z = sum(adj)
        votes = [int(counted * a / z) for a in adj]
        votes[max(range(len(votes)), key=votes.__getitem__)] += counted - sum(votes)
        total_cast = int(counted / 0.92)
        el_ap = int(E * f)
        out = [{"id": c["id"], "num": c["num"], "nome": c["nome"], "partido": c["partido"],
                "votos": v, "eleito": False, "status": ""} for c, v in zip(cands, votes)]
        return make_result(key, cargo, nome, ts_, ap, E, total_cast,
                           max(el_ap - total_cast, 0), int(total_cast * 0.03), int(total_cast * 0.05), out)

    def snapshot(self, t: float) -> dict:
        data = {}
        for cargo in CARGOS:
            units = {}
            for u in self.muns:
                k = f"mun:{u['id']}"
                units[k] = self._unit(cargo, k, u["nome"], u, t)
            if CARGOS[cargo]["national"]:
                for u in self.ufs:
                    k = f"uf:{u['id']}"
                    units[k] = self._unit(cargo, k, u["nome"], u, t)
            data[cargo] = units
        return data


class MockSource:
    def __init__(self, municipios):
        self.municipios = municipios
        self.world = None
        self.t0 = time.time()

    async def init(self):
        self.world = MockWorld(self.municipios)
        self.t0 = time.time()

    async def fetch(self):
        dur = settings.sim_minutes * 60
        el = time.time() - self.t0
        if settings.sim_loop:
            el = el % (dur * 1.15)
        return self.world.snapshot(min(el / dur, 1.0))
