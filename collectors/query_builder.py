"""
Gerador de queries por estratégia de coletor.

Produto cartesiano inteligente:
  cargos-alvo × termos júnior × localização = dezenas de queries distintas.
"""

# Cargos-alvo em PT e EN (par usado por diferentes fontes)
_ROLES: list[tuple[str, str]] = [
    ("PL/SQL Oracle banco de dados",     "PL/SQL Oracle database"),
    ("analista suporte técnico",          "technical support analyst"),
    ("analista sustentação sistemas",     "systems support analyst helpdesk"),
    ("cloud GCP Google Cloud",            "GCP Google Cloud engineer"),
    ("analista dados SQL",                "SQL data analyst"),
    ("product owner scrum kanban",        "product owner agile scrum"),
    ("desenvolvedor backend python",      "backend python developer"),
    ("service desk ITIL",                 "service desk ITSM"),
    ("DBA administrador banco dados",     "DBA database administrator"),
]

_JUNIOR_PT = ["junior", "júnior", "trainee", "estágio", "estagiário", "entry level"]
_JUNIOR_EN = ["junior", "trainee", "entry level", "intern"]
_LOCS_BR   = ["Brasil", "São Paulo", "remoto"]


def google_jobs_queries() -> list[str]:
    """
    Queries para SerpAPI (Google Jobs) — buscam diretamente no Google,
    que já agrega Gupy, LinkedIn, Indeed, Vagas.com, etc.
    Usar strings em português para máximo de resultados brasileiros.
    """
    queries: list[str] = []
    for pt, _ in _ROLES:
        queries.append(f"{pt} junior OR júnior Brasil")
        queries.append(f"{pt} trainee OR estagiário remoto")
    # Queries genéricas de alto volume
    queries += [
        "estágio TI tecnologia informação Brasil 2025",
        "trainee tecnologia informação Brasil 2025",
        "desenvolvedor junior remoto Brasil",
        "analista junior TI Brasil",
        "vaga junior backend remoto",
        "vaga junior dados SQL Brasil",
        "oportunidade júnior cloud Brasil",
        "estagiário desenvolvimento sistemas São Paulo",
        "analista suporte júnior remoto",
        "PL SQL Oracle júnior São Paulo",
    ]
    return queries


def brazil_api_queries() -> list[str]:
    """
    Para Adzuna e JSearch — buscas localizadas em PT e EN.
    """
    queries: list[str] = []
    for pt, en in _ROLES:
        for term in ["junior", "júnior", "trainee"]:
            queries.append(f"{pt} {term}")
        queries.append(f"{en} junior")
    queries += ["estagiário programação Brasil", "trainee TI", "analista junior TI"]
    return queries


def remote_queries() -> list[str]:
    """
    Para Remotive, RemoteOK, Arbeitnow — vagas remotas internacionais.
    Usar EN pois essas plataformas são majoritariamente em inglês.
    """
    queries: list[str] = []
    for _, en in _ROLES:
        queries.append(f"{en} junior remote")
    queries += [
        "SQL junior remote",
        "python junior remote",
        "cloud junior remote",
        "data analyst junior remote",
    ]
    return queries


def tag_queries() -> list[str]:
    """
    Tags para APIs que buscam por tag (RemoteOK, Arbeitnow).
    """
    return ["sql", "python", "cloud", "junior", "oracle", "gcp", "support", "data", "product"]


def themuse_categories() -> list[str]:
    """
    Categorias para The Muse API.
    """
    return [
        "Software Engineer",
        "Data & Analytics",
        "Product Management",
        "IT & Systems",
        "Customer Support",
    ]
