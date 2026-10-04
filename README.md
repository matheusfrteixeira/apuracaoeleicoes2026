# Apuração 2026 — MVP

Backend **FastAPI** (REST + WebSocket) · Front **Vue 3 + Pinia** · cache **Redis** (ou memória em dev).

```
TSE (JSON) ──► Ingestor ──► normaliza → agrega → projeta ──► Redis ──pub/sub──► API/WebSocket ──► Vue
 (ou mock)     (1 worker)                                    (bytes JSON)                      (mapa, gráficos)
```

## Rodar em desenvolvimento (sem Docker, sem Redis)

```bash
# terminal 1 – backend (modo simulador: dados fictícios, 167 municípios do RN + 26 UFs)
cd backend && pip install -r requirements.txt
SIM_MINUTES=6 uvicorn app.main:app --reload --port 8000

# terminal 2 – frontend
cd frontend && npm install && npm run dev        # http://localhost:5173
```

## Rodar com Redis (produção-like)

```bash
docker compose up --build        # http://localhost:8080
DATA_MODE=tse docker compose up  # lê o JSON do TSE em vez do simulador
```

## Variáveis principais (`backend/app/config.py`)

| Variável | Padrão | O que faz |
|---|---|---|
| `DATA_MODE` | `mock` | `mock` = simulador · `tse` = lê o TSE |
| `TSE_BASE` | `https://resultados.tse.jus.br/oficial/ele2026/6259/dados` | base da URL do TSE |
| `TSE_ELE_FED` | `6257` | id da eleição federal oficial (Presidente) |
| `TSE_ELE_EST` | `6259` | id da eleição estadual oficial (Governador, Senador, Dep. Federal, Dep. Estadual) |
| `POLL_SECONDS` / `POLL_MINUTES` | `300` (5 min) | intervalo de coleta no modo `tse` (em segundos ou minutos) |
| `TSE_FETCH_MUNICIPALITIES` | `true` | `true` = busca os 167 municípios do RN (alimenta mapa e tabela); `false` = apenas consolidados |
| `TSE_FETCH_OTHER_UFS` | `false` | `false` = busca apenas UF configurada e BR; `true` = busca todas as 26 outras UFs para o mapa nacional |
| `REDIS_URL` | vazio | vazio = memória; `redis://...` = Redis |
| `INGEST_EMBEDDED` | `true` | `false` = API não ingere; rode `python -m app.worker` |
| `SIM_MINUTES` / `SIM_LOOP` | `6` / `true` | duração do simulador e se reinicia ao terminar |

## Endpoints

- `WS /ws` — envia `{"op":"sub","cargo":"3","scope":"mun:2408102"}`; recebe `meta, national, map, result, hist, hist_point`.
- `GET /api/map/{cargo}` — líder, projeção e % apurado de todos os municípios (1 payload, ~25 KB / ~4 KB gzip).
- `GET /api/results/{cargo}/{scope}` — `scope` = `br` · `uf:RN` · `mun:<codigo IBGE>`.
- `GET /api/history/{cargo}/{scope}` · `GET /api/geo` · `GET /api/municipios` · `GET /api/health`

## Por que é rápido

1. Ingestão **fora** do caminho de leitura: o worker calcula tudo e grava no Redis já como JSON.
2. A API devolve os **bytes do Redis direto** (sem decodificar/recodificar) e o WebSocket monta a mensagem por concatenação de bytes.
3. O servidor só empurra o que cada cliente está **olhando** (cargo + escopo) — e só quando aquele cargo mudou.
4. Requisições condicionais (`ETag`) ao TSE; só reprocessa o que mudou.
5. Front: `shallowRef` para payloads grandes, geometria do mapa calculada 1x, gráficos Canvas.

## Como funciona a projeção (`backend/app/forecast.py`)

Por município/UF: total final ≈ votos apurados ÷ fração de seções apuradas; os votos restantes seguem a
participação observada, suavizada por um prior (resultado do nível acima) quando há poucas urnas.
Incerteza = ruído multinomial + **erro sistemático da ordem de apuração** (parte comum a todas as unidades
+ parte própria). A chance de vitória e de 2º turno saem de uma aproximação normal sobre a diferença
entre os candidatos. No simulador, o intervalo de 95% cobriu o resultado final em todos os checkpoints testados.

## Limitações do MVP (próximos passos)

- **Deputados**: ranking por votos nominais. Falta quociente eleitoral/partidário e sobras (D'Hondt) para dizer quem é eleito.
- **Votos de legenda** não entram no total dos proporcionais.
- **2º turno** não está modelado (só a probabilidade de ele acontecer).
- Calibrar `K_COMMON`/`K_IDIO` com a apuração de 2022 (e do simulado) antes do dia.
- Histórico de projeção só para Brasil e UF (não por município).
- Sem autenticação/rate-limit; adicione no proxy se for público.

## Testes rápidos

```bash
cd backend
python tests/sim_check.py     # projeção converge e o IC cobre o resultado final
python tests/tse_check.py     # parser contra amostra real do TSE
python tests/redis_check.py   # RedisStore + pub/sub (usa fakeredis)
```
