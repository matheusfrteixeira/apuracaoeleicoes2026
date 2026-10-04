import os


class Settings:
    def __init__(self):
        # redis://localhost:6379/0  -> usa Redis. Vazio -> cache em memoria (dev).
        self.redis_url: str = os.getenv("REDIS_URL", "")
        # mock = simulador local | tse = le o JSON do TSE (simulado ou oficial)
        self.data_mode: str = os.getenv("DATA_MODE", "tse")
        self.tse_base: str = os.getenv(
            "TSE_BASE",
            "https://resultados.tse.jus.br/oficial/ele2026/6259/dados",
        )
        self.tse_ele: str = os.getenv("TSE_ELE", "6259")
        # Códigos de eleição oficial: federal 6257 (Presidente) e estadual 6259 (Governador, Senador, Deputados)
        self.tse_ele_fed: str = os.getenv("TSE_ELE_FED", "6257")
        self.tse_ele_est: str = os.getenv("TSE_ELE_EST", os.getenv("TSE_ELE", "6259"))

        # Intervalo entre requisicoes ao TSE (padrao: 5 minutos = 300s).
        # Parametrizavel via POLL_SECONDS (em segundos) ou POLL_MINUTES (em minutos).
        self.poll_seconds: float = float(
            os.getenv("POLL_SECONDS")
            or (float(os.getenv("POLL_MINUTES")) * 60 if os.getenv("POLL_MINUTES") else 300)
        )
        self.tse_concurrency: int = int(os.getenv("TSE_CONCURRENCY", "40"))
        # Se True, busca dados dos 167 municipios do estado (alimenta o mapa e a tabela de cidades)
        self.tse_fetch_municipalities: bool = (
            os.getenv("TSE_FETCH_MUNICIPALITIES", "true").lower() == "true"
        )
        # Se False, nao busca arquivos individuais das outras 26 UFs (ex: TO, SP, etc.)
        self.tse_fetch_other_ufs: bool = (
            os.getenv("TSE_FETCH_OTHER_UFS", "false").lower() == "true"
        )
        self.uf: str = os.getenv("UF", "RN")
        self.uf_ibge: int = int(os.getenv("UF_IBGE", "24"))
        # simulador
        self.sim_minutes: float = float(os.getenv("SIM_MINUTES", "6"))
        self.sim_loop: bool = os.getenv("SIM_LOOP", "true").lower() == "true"
        # ingestao dentro do processo da API (dev). Em prod: INGEST_EMBEDDED=false + worker separado.
        self.embedded: bool = os.getenv("INGEST_EMBEDDED", "true").lower() == "true"
        self.hist_cap: int = int(os.getenv("HIST_CAP", "1500"))
        default_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        self.data_dir: str = os.getenv("DATA_DIR", default_data)

        self.ibge_geo: str = (
            "https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}"
            "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=intermediaria"
        )
        self.ibge_muns: str = (
            "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{ibge}/municipios"
        )


settings = Settings()
