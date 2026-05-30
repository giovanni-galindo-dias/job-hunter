"""
Gerador de queries por estratégia de coletor.

ATUALIZADO com base no veredicto do conselho:
- Queries reposicionadas para "Analista de Dados Jr", "DBA Jr", "Analista Suporte Jr"
  em vez de "desenvolvedor júnior" genérico
- Foco no mercado corporativo brasileiro (bancos, fintechs, consultorias)
- Menos queries internacionais, mais especificidade por cargo-alvo
"""

# ── Cargos-alvo em PT e EN, ordenados por prioridade do perfil ────────────────
_ROLES: list[tuple[str, str]] = [
    # (PT, EN) — PT usado por fontes BR; EN por fontes internacionais
    ("PL/SQL Oracle banco de dados",       "PL/SQL Oracle database"),
    ("analista dados SQL Python",          "SQL data analyst junior"),
    ("DBA administrador banco de dados",   "DBA database administrator junior"),
    ("analista suporte técnico TI",        "IT technical support analyst junior"),
    ("analista sustentação sistemas",      "systems support analyst junior"),
    ("service desk ITIL helpdesk",         "service desk ITSM junior"),
    ("cloud GCP Google Cloud Platform",    "GCP Google Cloud engineer junior"),
    ("analista cloud DevOps",              "cloud DevOps junior"),
    ("product owner scrum kanban ágil",    "product owner agile scrum junior"),
    ("desenvolvedor backend python",       "backend python developer junior"),
]

# ── Fontes BR-específicas (Gupy tem suas próprias queries) ────────────────────
# Ver collectors/gupy.py para as queries otimizadas para o Gupy

def google_jobs_queries() -> list[str]:
    """
    Para SerpAPI (Google Jobs) — buscas no Google que já agrega
    Gupy, LinkedIn, Indeed, Vagas.com, Catho, InfoJobs, etc.
    Queries em PT-BR para máximo de resultados brasileiros.
    """
    queries: list[str] = []
    for pt, _ in _ROLES:
        queries.append(f"{pt} júnior Brasil")
        queries.append(f"{pt} trainee OR estagiário São Paulo OR remoto")

    # Queries de alto volume específicas para o perfil
    queries += [
        "analista dados júnior SQL Python Brasil",
        "DBA júnior Oracle SQL Server Brasil",
        "analista suporte júnior ServiceNow ITIL",
        "PL SQL Oracle júnior banco fintech Brasil",
        "cloud engineer júnior GCP AWS remoto Brasil",
        "estágio TI banco de dados São Paulo",
        "trainee tecnologia informação 2025 Brasil",
        "analista cloud ops júnior remoto Brasil",
        "product owner junior scrum agile Brasil",
        "estagiário desenvolvimento sistemas São Paulo",
    ]
    return queries


def brazil_api_queries() -> list[str]:
    """Para Adzuna e JSearch — queries localizadas em PT e EN."""
    queries: list[str] = []
    for pt, en in _ROLES:
        queries.append(f"{pt} junior")
        queries.append(f"{en} Brazil")
    queries += [
        "estagiário programação banco dados",
        "trainee TI banco de dados",
        "analista junior tecnologia informação",
    ]
    return queries


def remote_queries() -> list[str]:
    """Para Remotive, RemoteOK — vagas remotas internacionais em EN."""
    _, roles_en = zip(*_ROLES)
    return [f"{en} remote" for en in roles_en[:6]] + [
        "SQL data analyst junior remote",
        "cloud GCP junior remote",
        "python junior remote",
    ]


def tag_queries() -> list[str]:
    """Tags simples para APIs baseadas em tags (RemoteOK, Arbeitnow)."""
    return ["sql", "python", "cloud", "oracle", "gcp", "data", "support", "junior"]


def themuse_categories() -> list[str]:
    """Categorias para The Muse API (filtro entry-level nativo)."""
    return [
        "Software Engineer",
        "Data & Analytics",
        "IT & Systems",
        "Customer Support",
        "Product Management",
    ]
