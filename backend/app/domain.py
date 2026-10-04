"""Cargos e UFs. Codigos de cargo seguem o padrao do TSE (c0001 = Presidente...)."""

CARGOS = {
    "1": {"code": "1", "key": "presidente", "nome": "Presidente", "tipo": "majoritario", "vagas": 1, "national": True},
    "3": {"code": "3", "key": "governador", "nome": "Governador", "tipo": "majoritario", "vagas": 1, "national": False},
    "5": {"code": "5", "key": "senador", "nome": "Senador", "tipo": "majoritario", "vagas": 2, "national": False},
    "6": {"code": "6", "key": "dep_federal", "nome": "Deputado Federal", "tipo": "proporcional", "vagas": 8, "national": False},
    "7": {"code": "7", "key": "dep_estadual", "nome": "Deputado Estadual", "tipo": "proporcional", "vagas": 24, "national": False},
}

# sigla, nome, eleitorado aproximado (milhares) - usado so no simulador
UFS = [
    ("AC", "Acre", 590), ("AL", "Alagoas", 2360), ("AP", "Amapá", 540), ("AM", "Amazonas", 2640),
    ("BA", "Bahia", 11000), ("CE", "Ceará", 6600), ("DF", "Distrito Federal", 2200),
    ("ES", "Espírito Santo", 2900), ("GO", "Goiás", 4900), ("MA", "Maranhão", 4900),
    ("MT", "Mato Grosso", 2500), ("MS", "Mato Grosso do Sul", 2000), ("MG", "Minas Gerais", 16300),
    ("PA", "Pará", 6000), ("PB", "Paraíba", 3100), ("PR", "Paraná", 8400), ("PE", "Pernambuco", 7000),
    ("PI", "Piauí", 2500), ("RJ", "Rio de Janeiro", 12900), ("RN", "Rio Grande do Norte", 2600),
    ("RS", "Rio Grande do Sul", 8500), ("RO", "Rondônia", 1200), ("RR", "Roraima", 370),
    ("SC", "Santa Catarina", 5400), ("SP", "São Paulo", 34600), ("SE", "Sergipe", 1600),
    ("TO", "Tocantins", 1100),
]
UF_NAME = {s: n for s, n, _ in UFS}
