# 🎯 Job Hunter

Aplicação web local para encontrar, organizar e se candidatar a vagas de emprego de forma centralizada.

## Funcionalidades

| Seção | O que faz |
|---|---|
| **Vagas** | Busca agregada em Remotive, RemoteOK, Adzuna e Google Jobs com score de match 0-100 |
| **Kanban** | Arrastar e soltar vagas entre "Para Aplicar / Em Andamento / Entrevista / Encerrado" |
| **Respostas** | Banco de respostas pré-escritas para formulários (copiar com 1 clique) |
| **Carta** | Gerador de carta de apresentação personalizada com base na descrição da vaga |

## Instalação

### 1. Pré-requisitos
- Python 3.11+
- pip

### 2. Clonar/acessar a pasta
```bash
cd "job_hunter"
```

### 3. Criar ambiente virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 4. Instalar dependências
```bash
pip install -r requirements.txt
```

### 5. Configurar variáveis de ambiente (opcional)
```bash
cp .env.example .env
# Edite o .env com suas chaves de API
```

As APIs **Remotive** e **RemoteOK** são gratuitas e funcionam sem chave.  
Para Google Jobs via SerpAPI: https://serpapi.com (100 req/mês grátis)  
Para Adzuna: https://developer.adzuna.com (gratuito)

### 6. Executar
```bash
uvicorn main:app --reload --port 8000
```

Acesse: **http://localhost:8000**

## Estrutura do Projeto

```
job_hunter/
├── main.py               # FastAPI app, rotas principais
├── database.py           # SQLAlchemy + SQLite
├── models.py             # Modelo KanbanJob
├── profile.py            # Perfil do usuário (skills, experiência, cargos-alvo)
├── routers/
│   ├── jobs.py           # /api/jobs — busca e score de vagas
│   ├── kanban.py         # /api/kanban — CRUD Kanban (SQLite)
│   ├── answers.py        # /api/answers — respostas prontas
│   └── cover_letter.py   # /api/cover-letter — gerador de carta
├── services/
│   ├── fetcher.py        # Integração com APIs externas
│   ├── matcher.py        # Score de match perfil × vaga
│   └── cover_letter.py   # Lógica de geração de carta
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   └── index.html
├── .env.example
└── requirements.txt
```

## Personalização

Edite `profile.py` para atualizar:
- Skills técnicas (usadas no score de match)
- Cargos-alvo (usados nas buscas)
- Palavras-chave de busca
- Dados pessoais (carta de apresentação)

## APIs utilizadas

| API | Chave necessária | Limite gratuito |
|---|---|---|
| Remotive | Não | Sem limite |
| RemoteOK | Não | Sem limite |
| Adzuna | Sim | 250 req/dia |
| SerpAPI (Google Jobs) | Sim | 100 req/mês |

## Aviso

Esta aplicação **não realiza candidaturas automáticas**. Ela apenas localiza, organiza e gera textos de apoio. A candidatura sempre é feita manualmente pelo usuário na plataforma original.
