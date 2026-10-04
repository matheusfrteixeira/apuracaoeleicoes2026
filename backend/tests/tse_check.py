"""Parser contra um trecho FIEL do JSON do simulado do TSE (br-c0001-e021270-u.json)."""
import sys; sys.path.insert(0, ".")
from app.tse import parse_tse, TseSource, norm

sample = {"ele":"21270","dg":"29/09/2026","hg":"16:29:12","carg":[{"cd":"1","nmn":"Presidente","agr":[
 {"n":"60134540","tp":"i","par":[{"n":"68","sg":"P 9996","cand":[{"n":"68","sqcand":"41592494","nm":"CANDIDATO 9987","nmu":"CANDIDATO 9987","dvt":"Válido","e":"n","st":"Não eleito","vap":"9130869","pvap":"7,57"}]}]},
 {"n":"60134536","tp":"i","par":[{"n":"57","sg":"P 9998","cand":[{"n":"57","sqcand":"41592406","nm":"CANDIDATO 9999","nmu":"CANDIDATO 9999","dvt":"Anulado sub judice","e":"s","st":"2º turno","vap":"10503573","pvap":"8,71"}]}]}]}],
 "s":{"ts":"528951","st":"528951"},
 "e":{"te":"163079139","c":"138863131","a":"24215741"},
 "v":{"vb":"9118018","tvn":"9040537","vn":"9040537"}}
r = parse_tse(sample, "br", "Brasil", "1")
print(r["apuracao"], r["eleitorado"], r["votos"])
print([(c["nome"], c["votos"], c["pct"], c["status"]) for c in r["cand"]])
assert r["apuracao"]["pct"] == 100.0 and r["cand"][0]["votos"] == 10503573

s = TseSource([{"id": "2400109", "nome": "Acari"}, {"id": "2408102", "nome": "Natal"}])
s.tse_code = s._map_codes({"abr": [{"cd": "RN", "mu": [{"cd": "17612", "nm": "ACARI"}, {"cd": "17001", "nm": "NATAL"}]}]})
print("mapa IBGE->TSE:", s.tse_code)
for sc in ("br", "uf:RN", "uf:SP", "mun:2408102"):
    print(sc, "->", s._url("1", sc))
