# Perfil completo do usuário — base para match e geração de textos

PROFILE = {
    "name": "Giovanni Galindo Dias",
    "email": "giovannigdias1@gmail.com",
    "phone": "(12) 99173-0990",
    "location": "Guaratinguetá, São Paulo, Brasil",
    "linkedin": "linkedin.com/in/giovanni-galindo-dias",
    "github": "github.com/giovanni-galindo-dias",
    "remote": True,
    "immediate": True,
    "visa_sponsorship": False,  # não autorizado EUA/Canadá sem sponsorship

    "summary": (
        "Desenvolvedor Backend e Product Owner com experiência em sustentação "
        "de sistemas críticos, análise de dados relacionais (SQL, PL/SQL, Oracle) "
        "e liderança de times ágeis. Atuou na estabilização de sistemas usados por "
        "um dos maiores planos odontológicos da América Latina. "
        "Em especialização em Google Cloud Platform, com estudos voltados à "
        "certificação Associate Cloud Engineer (ACE)."
    ),

    "skills": [
        "SQL", "PL/SQL", "Oracle Database", "Oracle", "SQL Developer",
        "Python", "ServiceNow", "Google Cloud Platform", "GCP",
        "Docker", "REST API", "Git", "ITIL", "Scrum", "Kanban", "Agile",
        "FastAPI", "PostgreSQL", "Cloud Run", "Cloud SQL", "Cloud Storage",
        "Compute Engine", "GKE", "IAM", "Cloud Scheduler",
        "Product Owner", "Backlog", "Sprint", "Jira",
        "Java", "Sistemas Legados", "Sustentação", "Suporte", "Service Desk",
        "Análise de Dados", "ETL", "Relatórios", "ITSM",
    ],

    # skills agrupadas para exibição de match
    "skill_groups": {
        "Banco de Dados": ["SQL", "PL/SQL", "Oracle Database", "PostgreSQL", "SQL Developer"],
        "Cloud & DevOps": ["GCP", "Google Cloud Platform", "Docker", "Cloud Run", "Cloud SQL",
                           "Cloud Storage", "Compute Engine", "GKE", "IAM", "Cloud Scheduler"],
        "Backend": ["Python", "FastAPI", "REST API", "Java"],
        "Gestão": ["Scrum", "Kanban", "Product Owner", "Backlog", "Sprint", "Agile", "Jira", "ITIL", "ITSM"],
        "Suporte": ["ServiceNow", "Service Desk", "Sustentação", "ITIL"],
    },

    "experience": [
        {
            "role": "Product Owner | Gestor de Equipe Técnica",
            "company": "Liax Tecnologia",
            "period": "Jan 2026 – Fev 2026",
            "bullets": [
                "Liderou dois projetos simultâneos: sistema de OCR com IA para boletos bancários e redesign de design system enterprise.",
                "Priorização de backlog, planejamento de sprints, cerimônias ágeis (Scrum/Kanban): planning, review, retrospectiva e daily.",
                "Apresentações semanais de progresso ao cliente enterprise.",
            ],
        },
        {
            "role": "Desenvolvedor Backend Junior | Analista de Suporte",
            "company": "Liax Tecnologia",
            "period": "Out 2025 – Dez 2025",
            "bullets": [
                "Resolveu em média 50 requisições e 3 incidentes/mês via ServiceNow, com cumprimento de SLA.",
                "Análise e manipulação de bases relacionais com SQL e PL/SQL no Oracle Database: consultas complexas, ajuste de queries, extração de relatórios, correção de inconsistências.",
                "Sustentação de sistemas corporativos críticos de um dos maiores planos odontológicos da América Latina.",
                "Análise de bases Java em sistemas legados para identificar causa-raiz de incidentes.",
            ],
        },
        {
            "role": "Estagiário em Inovação e Gestão de Demandas",
            "company": "Prefeitura Municipal de Guaratinguetá",
            "period": "Jan 2025 – Out 2025",
            "bullets": [
                "Gestão de demandas junto a investidores, empresários e stakeholders.",
                "Documentação de processos administrativos e fluxos de atendimento.",
            ],
        },
    ],

    "education": [
        "Tecnólogo em Gestão da Tecnologia da Informação — FATEC Guaratinguetá (concluído)",
        "Técnico em Desenvolvimento de Sistemas — ETEC Prof. Alfredo de Barros Santos (concluído)",
    ],

    "certifications_in_progress": [
        "Google Cloud Associate Cloud Engineer (ACE) — Compute Engine, Cloud Storage, IAM, GKE, Cloud Operations",
    ],

    "projects": [
        {
            "name": "DB Cloud Monitor",
            "url": "github.com/giovanni-galindo-dias/db-cloud-monitor",
            "description": (
                "Sistema de monitoramento de bancos Oracle e PostgreSQL com arquitetura GCP-Ready. "
                "Abre incidentes automaticamente via trigger SQL, gerencia SLA por severidade, "
                "captura slow queries, dashboard em tempo real via REST API. "
                "Stack: Python, SQL, Docker, Cloud Run, Cloud SQL, Cloud Scheduler."
            ),
        }
    ],

    "languages": ["Português (nativo)", "Inglês B2 (TOEIC)", "Espanhol (intermediário)"],

    "target_roles": [
        "Desenvolvedor PL/SQL",
        "Desenvolvedor Oracle",
        "Analista de Suporte",
        "Analista de Sustentação",
        "Service Desk",
        "Analista Cloud",
        "Cloud Ops",
        "Analista de Dados",
        "Product Owner",
        "Analista de Produto",
    ],

    # palavras-chave para busca nas APIs
    "search_keywords": [
        "PL/SQL junior",
        "Oracle database junior",
        "analista suporte junior",
        "analista sustentacao",
        "cloud ops GCP junior",
        "analista dados junior",
        "product owner junior",
        "backend python junior",
        "SQL developer junior",
    ],

    "salary_expectation": "A combinar conforme responsabilidades e benefícios",
    "work_model": "Remoto ou híbrido — aberto a presencial na região do Vale do Paraíba/SP",
}
