"""Valida pipeline + projecao: a projecao em t=0.3/0.5 deve se aproximar do resultado final."""
import asyncio, sys, time
sys.path.insert(0, ".")
from app import ibge
from app.mock import MockWorld
from app.pipeline import build_cargo

async def main():
    muns = await ibge.load_municipios()
    w = MockWorld(muns)
    final = {}
    for t in (1.0, 0.15, 0.3, 0.5, 0.8):
        t0 = time.time()
        data = w.snapshot(t)
        t1 = time.time()
        for cargo in ("1", "3", "6"):
            b = build_cargo(cargo, data[cargo], time.time())
            rn = b["results"]["uf:RN"]; fc = rn["forecast"]
            top = fc["proj"][0]
            if t == 1.0:
                final[cargo] = {p["id"]: rn["cand"][i]["pct"] for i, p in enumerate(fc["proj"][:1])}
                final[cargo] = {c["id"]: c["pct"] for c in rn["cand"]}
            err = abs(top["pct"] - final.get(cargo, {}).get(top["id"], top["pct"]))
            print(f"t={t:.2f} cargo={cargo} apur={rn['apuracao']['pct']:5.1f}% lider={top['nome'] if 'nome' in top else top['id']} "
                  f"proj={top['pct']:5.2f} [{top['lo']:.1f}-{top['hi']:.1f}] erro_vs_final={err:.2f}pp prob={fc['prob']} p2t={fc['p2t']}")
        print(f"   snapshot {1000*(t1-t0):.0f}ms, 3x build {1000*(time.time()-t1):.0f}ms")
    b = build_cargo("1", w.snapshot(0.5)["1"], 0)
    br = b["results"]["br"]; print("BR:", br["apuracao"], br["forecast"]["prob"], "p2t", br["forecast"]["p2t"], "ufs:", len(br["by_uf"]))
    import orjson
    print("map payload bytes:", len(orjson.dumps(b["map"])), "items:", len(b["map"]["items"]))
asyncio.run(main())
