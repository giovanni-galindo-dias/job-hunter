"""
FIT_SCORE — aderência do perfil do usuário à vaga.
Usa pesos por skill e bônus por tipo de cargo-alvo.
"""
import re
from profile import PROFILE

# Skills com peso diferenciado (padrão = 1.0)
SKILL_WEIGHTS: dict[str, float] = {
    "PL/SQL": 3.0,
    "Oracle Database": 3.0,
    "Oracle": 2.5,
    "SQL": 2.0,
    "SQL Developer": 2.0,
    "ServiceNow": 2.0,
    "Google Cloud Platform": 2.0,
    "GCP": 2.0,
    "Python": 2.0,
    "Docker": 1.5,
    "REST API": 1.5,
    "ITIL": 1.5,
    "Scrum": 1.2,
    "Kanban": 1.2,
}

# Tipo de cargo → bônus de pontos (alinha com prioridades do perfil)
ROLE_TYPE_BONUS: dict[str, int] = {
    "sql":     22,   # 1. Desenvolvedor PL/SQL / Oracle
    "support": 22,   # 2. Analista de Suporte / Sustentação
    "cloud":   15,   # 3. Analista Cloud / GCP
    "data":    12,   # 4. Analista de Dados
    "po":      8,    # 5. Product Owner
    "generic": 0,
}


def _normalize(text: str) -> str:
    return text.lower()


def _detect_role_type(title: str, description: str) -> str:
    combined = _normalize(f"{title} {description}")
    if any(w in combined for w in ["pl/sql", "plsql", "oracle", "banco de dados", "database"]):
        return "sql"
    if any(w in combined for w in ["suporte", "sustentação", "sustentacao", "service desk", "helpdesk", "itsm", "itil", "incidente", "chamado"]):
        return "support"
    if any(w in combined for w in ["cloud", "gcp", "google cloud", "aws", "azure", "devops", "kubernetes", "k8s"]):
        return "cloud"
    if any(w in combined for w in ["dados", "data analyst", "analytics", "bi ", "business intelligence", "etl", "data engineer"]):
        return "data"
    if any(w in combined for w in ["product owner", " po ", "backlog", "produto", "roadmap"]):
        return "po"
    return "generic"


def score_fit(title: str, description: str) -> dict:
    """
    Retorna fit_score (0-100) e skills que deram match.
    """
    combined = _normalize(f"{title} {description}")
    skills = PROFILE["skills"]
    matched = []
    weighted_hits = 0.0
    max_possible = sum(SKILL_WEIGHTS.get(s, 1.0) for s in skills)

    for skill in skills:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, combined):
            matched.append(skill)
            weighted_hits += SKILL_WEIGHTS.get(skill, 1.0)

    # Score base: proporção ponderada (peso 70%)
    base = (weighted_hits / max(max_possible, 1)) * 70

    # Bônus por tipo de cargo (peso 22%)
    role_bonus = ROLE_TYPE_BONUS.get(_detect_role_type(title, description), 0)

    # Bônus por nivel junior detectado no título (peso 8%)
    junior_bonus = 8 if any(
        w in _normalize(title)
        for w in ["junior", "júnior", "jr", "trainee", "estágio", "estagiário"]
    ) else 0

    raw = base + role_bonus + junior_bonus
    fit_score = min(round(raw), 100)

    return {"fit_score": fit_score, "matched_skills": matched, "role_type": _detect_role_type(title, description)}
