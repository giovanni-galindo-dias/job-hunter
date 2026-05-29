from fastapi import APIRouter
from profile import PROFILE

router = APIRouter()

QUICK_ANSWERS = [
    {
        "id": 1,
        "category": "Apresentação",
        "question": "Fale sobre você",
        "answer": (
            f"Sou {PROFILE['name']}, Desenvolvedor Backend e Product Owner com formação em Gestão da Tecnologia da Informação "
            f"pela FATEC Guaratinguetá. Tenho experiência em sustentação de sistemas corporativos críticos, "
            f"análise de dados com SQL, PL/SQL e Oracle Database, além de liderança de times ágeis com Scrum e Kanban. "
            f"Atuei na Liax Tecnologia, onde sustentei sistemas de um dos maiores planos odontológicos da América Latina "
            f"e liderei projetos de OCR com IA e redesign de design system. "
            f"Estou em especialização em Google Cloud Platform, estudando para a certificação ACE, "
            f"e sou um desenvolvedor orientado a resultados, focado em qualidade e cumprimento de SLA."
        ),
    },
    {
        "id": 2,
        "category": "Pretensão Salarial",
        "question": "Qual sua pretensão salarial?",
        "answer": (
            "Estou aberto a discutir a remuneração com base nas responsabilidades da posição e no pacote de benefícios oferecido. "
            "Minha expectativa é de uma remuneração compatível com o mercado para o cargo e meu nível de experiência. "
            "Pode me informar a faixa salarial prevista para a vaga?"
        ),
    },
    {
        "id": 3,
        "category": "Autorização de Trabalho",
        "question": "Você está autorizado a trabalhar no Brasil?",
        "answer": "Sim, sou cidadão brasileiro, residente em Guaratinguetá — SP, e não há qualquer restrição para trabalho no Brasil.",
    },
    {
        "id": 4,
        "category": "Autorização de Trabalho",
        "question": "Você precisa de patrocínio de visto para trabalhar nos EUA/Canadá?",
        "answer": (
            "Sim, precisaria de patrocínio de visto para trabalhar presencialmente nos EUA ou Canadá. "
            "Para posições totalmente remotas com contrato brasileiro ou PJ internacional, não há necessidade de visto."
        ),
    },
    {
        "id": 5,
        "category": "Experiência",
        "question": "Qual seu nível de experiência?",
        "answer": (
            "Tenho aproximadamente 1 ano de experiência profissional formal, atuando em nível júnior/pleno inicial. "
            "Trabalhei com sustentação de sistemas críticos, análise de dados em Oracle Database, "
            "gestão ágil de projetos e desenvolvimento de soluções backend em Python. "
            "Complemento minha experiência com projetos pessoais práticos e certificações em andamento."
        ),
    },
    {
        "id": 6,
        "category": "Comportamental",
        "question": "Como você lida com prazos apertados?",
        "answer": (
            "Na Liax Tecnologia, o cumprimento de SLA era não-negociável — resolvia em média 50 requisições e 3 incidentes por mês, "
            "muitos com janelas curtas. Meu processo é: priorizar pelo impacto, comunicar rapidamente qualquer risco de prazo "
            "ao responsável, dividir o problema em partes menores e buscar ajuda quando necessário. "
            "Acredito que clareza e comunicação proativa são tão importantes quanto a execução técnica."
        ),
    },
    {
        "id": 7,
        "category": "Comportamental",
        "question": "Por que você está saindo do emprego atual?",
        "answer": (
            "Estou em busca de um novo desafio profissional que me permita aprofundar minha atuação técnica e crescer "
            "em um ambiente estruturado. Quero continuar evoluindo em áreas como banco de dados, cloud e desenvolvimento backend, "
            "contribuindo de forma significativa em um time sólido."
        ),
    },
    {
        "id": 8,
        "category": "Motivação",
        "question": "Por que você quer trabalhar nessa empresa?",
        "answer": (
            "Pesquisei sobre a empresa e me identifiquei com a cultura e os desafios técnicos que ela apresenta. "
            "Acredito que posso contribuir desde o início com minha experiência em SQL/PL/SQL, sustentação de sistemas "
            "e mentalidade orientada a SLA, enquanto continuo crescendo profissionalmente. "
            "Estou à disposição para compartilhar mais sobre minhas motivações específicas em uma conversa."
        ),
    },
    {
        "id": 9,
        "category": "Objetivos",
        "question": "Quais são seus objetivos profissionais?",
        "answer": (
            "No curto prazo, quero consolidar minha carreira como desenvolvedor backend/analista de dados, "
            "obtendo a certificação Google Cloud ACE e aprofundando minha expertise em Oracle e PL/SQL. "
            "No médio prazo, aspiro a liderar projetos técnicos com maior autonomia, "
            "combinando minha experiência em Product Owner com habilidades de engenharia de dados na nuvem."
        ),
    },
    {
        "id": 10,
        "category": "Disponibilidade",
        "question": "Quando você pode começar?",
        "answer": "Tenho disponibilidade imediata para iniciar. Prefiro trabalho remoto ou híbrido, mas estou aberto a discutir o modelo conforme a necessidade da empresa.",
    },
    {
        "id": 11,
        "category": "Modelo de trabalho",
        "question": "Você aceita trabalho presencial?",
        "answer": (
            "Estou localizado em Guaratinguetá — SP (Vale do Paraíba). "
            "Aceito trabalho presencial na região ou em São Paulo capital, além de remoto e híbrido. "
            "Para posições fora dessa área, prefiro modelo remoto ou híbrido com deslocamentos pontuais."
        ),
    },
    {
        "id": 12,
        "category": "Técnico",
        "question": "Quais ferramentas/tecnologias você domina?",
        "answer": (
            "Meu stack principal inclui: SQL e PL/SQL com Oracle Database e SQL Developer, Python (FastAPI, REST API), "
            "Docker, Google Cloud Platform (Compute Engine, Cloud Run, Cloud SQL, Cloud Storage, IAM, GKE, Cloud Scheduler), "
            "ServiceNow para gestão de incidentes e ITIL, Git para versionamento, "
            "e Scrum/Kanban para gestão ágil. Inglês avançado B2 (TOEIC)."
        ),
    },
]


@router.get("/")
def get_answers(category: str = ""):
    if category:
        filtered = [a for a in QUICK_ANSWERS if a["category"].lower() == category.lower()]
    else:
        filtered = QUICK_ANSWERS
    return {"answers": filtered}


@router.get("/categories")
def get_categories():
    cats = sorted(set(a["category"] for a in QUICK_ANSWERS))
    return {"categories": cats}
