"""
Gerador de carta de apresentação personalizada.
Usa template inteligente cruzando a vaga com o perfil do usuário.
"""
import re
from profile import PROFILE
from services.matcher import score_fit as score_job


def _extract_keywords(text: str) -> list[str]:
    """Extrai palavras relevantes do anúncio da vaga."""
    text_lower = text.lower()
    found = []
    for skill in PROFILE["skills"]:
        if skill.lower() in text_lower:
            found.append(skill)
    return found


def _pick_most_relevant_experience(keywords: list[str]) -> list[dict]:
    """Retorna as experiências do perfil mais relevantes para a vaga."""
    keyword_lower = [k.lower() for k in keywords]
    scored = []
    for exp in PROFILE["experience"]:
        combined = (exp["role"] + " " + " ".join(exp["bullets"])).lower()
        hits = sum(1 for kw in keyword_lower if kw in combined)
        scored.append((hits, exp))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored]


def _detect_role_type(title: str, description: str) -> str:
    combined = (title + " " + description).lower()
    if any(w in combined for w in ["pl/sql", "oracle", "plsql", "database", "banco de dados"]):
        return "sql"
    if any(w in combined for w in ["cloud", "gcp", "google cloud", "aws", "azure", "devops", "kubernetes"]):
        return "cloud"
    if any(w in combined for w in ["suporte", "sustentação", "service desk", "helpdesk", "itsm", "itil", "incidente"]):
        return "support"
    if any(w in combined for w in ["dados", "data", "analytics", "bi", "business intelligence", "etl"]):
        return "data"
    if any(w in combined for w in ["product owner", "po ", "produto", "backlog", "sprint", "scrum master"]):
        return "po"
    return "generic"


def generate(job_title: str, company: str, job_description: str) -> str:
    keywords = _extract_keywords(job_description)
    match = score_job(job_title, job_description)  # returns {fit_score, matched_skills, role_type}
    role_type = _detect_role_type(job_title, job_description)
    experiences = _pick_most_relevant_experience(keywords)
    profile = PROFILE

    # Intro personalizada por tipo de vaga
    intros = {
        "sql": (
            f"Sou Desenvolvedor Backend com sólida experiência em SQL, PL/SQL e Oracle Database, "
            f"adquirida durante a sustentação de sistemas críticos na Liax Tecnologia, onde atendi "
            f"em média 50 requisições e 3 incidentes mensais via ServiceNow, sempre dentro do SLA."
        ),
        "cloud": (
            f"Sou Desenvolvedor Backend com foco crescente em Google Cloud Platform, "
            f"estudando para a certificação Associate Cloud Engineer (ACE). "
            f"Meu projeto pessoal DB Cloud Monitor, disponível no GitHub, demonstra na prática "
            f"minha aplicação de Cloud Run, Cloud SQL, Cloud Scheduler e Docker em arquitetura GCP-Ready."
        ),
        "support": (
            f"Sou Analista de Suporte com experiência comprovada em sustentação de sistemas corporativos críticos, "
            f"gestão de incidentes via ServiceNow e cumprimento rigoroso de SLA. "
            f"Na Liax Tecnologia, resolvi em média 50 requisições e 3 incidentes por mês, "
            f"com análise de causa-raiz em bases Java de sistemas legados."
        ),
        "data": (
            f"Sou profissional com forte base em análise de dados relacionais — SQL, PL/SQL e Oracle Database — "
            f"aplicada em cenários críticos de produção. "
            f"Tenho experiência em consultas complexas, ajuste de queries, extração de relatórios "
            f"e correção de inconsistências em bases de grande volume."
        ),
        "po": (
            f"Sou Product Owner com experiência na liderança de projetos ágeis simultâneos, "
            f"incluindo um sistema de OCR com IA e um redesign de design system enterprise. "
            f"Conduzo cerimônias Scrum e Kanban (planning, review, retrospectiva, daily) "
            f"e tenho perfil técnico sólido, o que facilita a comunicação com times de desenvolvimento."
        ),
        "generic": (
            f"Sou Desenvolvedor Backend e Product Owner com experiência em sustentação de sistemas "
            f"críticos, análise de dados relacionais e liderança ágil. "
            f"Meu histórico inclui atuação em um dos maiores planos odontológicos da América Latina, "
            f"com foco em qualidade, SLA e resolução de problemas complexos."
        ),
    }

    intro = intros[role_type]

    # Parágrafo de skills matched
    if match["matched_skills"]:
        skills_str = ", ".join(match["matched_skills"][:8])
        skills_para = (
            f"Identifico forte alinhamento entre meu perfil e os requisitos da vaga. "
            f"Tenho experiência direta com: {skills_str}."
        )
    else:
        skills_para = (
            f"Acredito que meu perfil técnico e minha capacidade de aprendizado acelerado "
            f"se alinham bem com os desafios desta posição."
        )

    # Parágrafo de experiência mais relevante
    exp_para = ""
    if experiences:
        best = experiences[0]
        bullet = best["bullets"][0]
        exp_para = (
            f"Como {best['role']} na {best['company']} ({best['period']}), "
            f"{bullet[0].lower() + bullet[1:]}."
        )

    # Projeto pessoal se relevante
    project_para = ""
    if role_type in ("cloud", "sql", "data", "generic"):
        project_para = (
            f"Desenvolvi o DB Cloud Monitor (github.com/giovanni-galindo-dias/db-cloud-monitor), "
            f"um sistema de monitoramento de bancos Oracle e PostgreSQL com arquitetura GCP-Ready, "
            f"que abre incidentes automaticamente, gerencia SLA por severidade e expõe dashboard "
            f"em tempo real via REST API — demonstrando minha capacidade de entregar soluções "
            f"completas de ponta a ponta."
        )

    # Fechamento
    company_mention = f"na {company}" if company else "nessa empresa"
    closing = (
        f"Estou disponível de forma imediata para trabalho remoto ou híbrido, "
        f"e acredito que minha combinação de habilidades técnicas e experiência em ambientes "
        f"de alta demanda pode gerar valor real {company_mention}. "
        f"Fico à disposição para uma conversa e agradeço a oportunidade."
    )

    paragraphs = [
        f"Prezados(as) recrutadores(as) {company_mention},",
        "",
        intro,
        "",
        skills_para,
        "",
    ]

    if exp_para:
        paragraphs += [exp_para, ""]

    if project_para:
        paragraphs += [project_para, ""]

    paragraphs += [
        closing,
        "",
        f"Atenciosamente,",
        f"{profile['name']}",
        f"{profile['email']} | {profile['phone']}",
        f"LinkedIn: {profile['linkedin']}",
        f"GitHub: {profile['github']}",
    ]

    return "\n".join(paragraphs)
