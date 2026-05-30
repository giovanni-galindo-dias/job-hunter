# Job Hunter — Contexto completo do projeto

## O que é

Aplicação web local para encontrar e organizar vagas de emprego de **nível júnior no Brasil**. Roda em `http://localhost:8000`. **Não faz candidaturas automáticas** — apenas localiza, organiza e gera textos de apoio.

**Repositório:** https://github.com/giovanni-galindo-dias/job-hunter  
**Stack:** Python 3.10+ · FastAPI · SQLAlchemy · SQLite · HTML/CSS/JS puro (tema escuro)  
**Linhas de código:** ~4.100 (excluindo venv)

---

## Dono do projeto

**Giovanni Galindo Dias** — Desenvolvedor Backend Jr · Guaratinguetá-SP  
~1 ano de experiência | Skills: SQL, PL/SQL, Oracle, Python, GCP, ServiceNow, Docker  
Cargos-alvo: PL/SQL Jr > Suporte Jr > Cloud GCP Jr > Analista Dados Jr > PO Jr

---

## Estrutura de arquivos

```
job_hunter/
├── main.py                        FastAPI app + rotas
├── database.py                    SQLAlchemy + SQLite (job_hunter.db)
├── models.py                      KanbanJob + CollectedJob (cache)
├── profile.py                     Perfil completo do usuário (skills, experiência, pesos)
│
├── collectors/                    ← Arquitetura plugável de fontes
│   ├── base.py                    BaseCollector + RawJob (interface comum)
│   ├── registry.py                Lista de coletores ativos (BR-first)
│   ├── query_builder.py           Queries por cargo-alvo × nível × localização
│   ├── gupy.py                    🇧🇷 Gupy (maior plataforma RH do Brasil, sem chave)
│   ├── serpapi_google.py          Google Jobs via SerpAPI (agrega Gupy/LinkedIn/Indeed BR)
│   ├── adzuna.py                  Adzuna (endpoint Brasil, chave gratuita)
│   ├── jsearch.py                 JSearch via RapidAPI (LinkedIn/Indeed/Glassdoor)
│   ├── arbeitnow.py               Arbeitnow (remoto, sem chave)
│   ├── remotive.py                Remotive (remoto, sem chave)
│   ├── remoteok.py                RemoteOK (remoto, sem chave)
│   └── themuse.py                 The Muse (entry-level filter, sem chave)
│
├── services/
│   ├── aggregator.py              Orquestrador: paralelo → dedup → geo-filter → score → cache
│   ├── seniority_filter.py        Filtro de senioridade em 4 camadas (módulo isolado)
│   ├── matcher.py                 FIT_SCORE ponderado por skill e cargo-alvo
│   ├── cover_letter.py            Gerador de carta de apresentação por tipo de vaga
│   └── fetcher.py                 (legado — substituído por aggregator.py)
│
├── routers/
│   ├── jobs.py                    GET /search, /cache, /score, /keywords
│   ├── kanban.py                  CRUD kanban + /stats (conversão por fonte)
│   ├── answers.py                 Banco de 12 respostas prontas por categoria
│   └── cover_letter.py            POST /generate
│
├── static/css/style.css           Tema escuro, responsivo, badges de senioridade
├── static/js/app.js               SPA completo (4 abas)
├── templates/index.html           UI principal
│
├── tests/
│   └── test_seniority_filter.py   37 testes unitários (pytest)
│
├── .env.example                   Todas as chaves de API documentadas
├── .gitignore                     venv/, .env, *.db
├── requirements.txt               10 dependências
└── README.md                      Instruções de instalação
```

---

## Como funciona o pipeline de vagas

```
8 coletores executados em paralelo (asyncio.gather)
    │
    ▼
Flatten → lista única de RawJob
    │
    ▼
Deduplicação por (titulo_normalizado, empresa_normalizada)
com prioridade de fonte: Gupy > Google Jobs > Adzuna > JSearch > ...
    │
    ▼
Geo-filter (opcional): descarta vagas sem localização BR
    │
    ▼
Filtragem de senioridade em 4 camadas:
  1. Queries já injetam "junior/trainee/estágio"
  2. Blacklist de título (20 padrões: senior/pleno/lead/staff/manager/architect...)
  3. Regex de anos na descrição (PT + EN): >4 anos → descarte; 3-4 → "Verificar"
  4. SENIORITY_SCORE 0-100 + FIT_SCORE 0-100 (pesos por skill e cargo)
    │
    ▼
Marca "is_new" para vagas < 48h
    │
    ▼
Ordenação: novas BR primeiro → seniority DESC → fit DESC
    │
    ▼
Upsert no cache SQLite (CollectedJob)
    │
    ▼
Retorno com stats por fonte
```

---

## Scores (dois por vaga)

### SENIORITY_SCORE (compatibilidade de nível)
| Score | Label       | Significado |
|-------|-------------|-------------|
| 80-100| Júnior      | Explicitamente junior/estágio/trainee no título + sinais na descrição |
| 55-79 | Júnior/Verificar | Junior implícito ou 3-4 anos exigidos (negociável no Brasil) |
| 40-54 | Ambíguo     | Sem indicador claro de nível (toggle para mostrar) |
| 0     | Sênior/Pleno| Descartado — blacklist no título ou >4 anos exigidos |

### FIT_SCORE (aderência ao perfil)
Pesos diferenciados: PL/SQL ×3 · Oracle ×2.5 · SQL ×2 · GCP ×2 · ServiceNow ×2 · Python ×2  
Bônus por tipo de cargo: SQL/Suporte +22 · Cloud +15 · Dados +12 · PO +8

---

## 4 funcionalidades da UI

### 1. Painel de Vagas
- Cards com título, empresa, local, fonte, SENIORITY_SCORE, FIT_SCORE, skills matched, sinais de nível
- 🇧🇷 badge para vagas BR · 🆕 NOVO (< 48h) com animação pulse
- Filtros: "Somente Brasil" · "Mostrar ambíguas" · Ordenação (senioridade/fit/data/Brasil)
- Stats por fonte com indicador de erro
- Botões: "Abrir vaga" · "+ Kanban" · "✉ Carta"

### 2. Kanban (drag-and-drop)
- Colunas: Para Aplicar → Em Andamento → Teste/Entrevista → Encerrado
- Mover para "Entrevista" auto-marca interview_scheduled
- Botão 📅 para toggle manual de entrevista
- Notas por vaga (modal)
- 📊 Conversão por fonte: total/entrevistas/ofertas/taxa por canal

### 3. Banco de Respostas Prontas
- 12 respostas por categoria: Apresentação, Pretensão Salarial, Autorização de Trabalho, Experiência, Comportamental, Motivação, Objetivos, Disponibilidade, Modelo de trabalho, Técnico
- Filtro por categoria · Botão "Copiar" com feedback visual

### 4. Gerador de Carta de Apresentação
- Detecta tipo de vaga (SQL/Cloud/Suporte/PO/Dados/Genérico)
- Personaliza intro, skills paragraph, experiência mais relevante, projeto pessoal, fechamento
- Usa dados reais do profile.py

---

## Fontes de vagas e chaves

| Fonte | Chave | Volume estimado | Mercado |
|---|---|---|---|
| **Gupy** | Não | 500-1800/busca | 🇧🇷 Brasil (#1) |
| **Google Jobs** (SerpAPI) | Sim — 100/mês | 300-700 BR | 🇧🇷 agrega tudo |
| **Adzuna** | Sim — 250/dia | 150-300 | 🇧🇷 Brasil endpoint |
| **JSearch** (RapidAPI) | Sim — 200/mês | 100-200 | 🌎 multi-portal |
| **Arbeitnow** | Não | 500-1200 | 🌎 remoto |
| **Remotive** | Não | 80-120 | 🌎 remoto |
| **RemoteOK** | Não | 50-100 | 🌎 remoto |
| **The Muse** | Não | 20-60 | 🌎 entry-level |

---

## Otimizações do LLM Council (implementadas)

O sistema passou por uma análise de 10 sub-agentes (5 advisors + 5 peer reviewers + chairman) usando o LLM Council. Principais otimizações implementadas:

1. **Gupy Collector** — ausência da maior plataforma BR era o gap #1
2. **Geo-filter Brasil-first** — toggle + flag 🇧🇷 + ordenação BR primeiro
3. **Badge NOVO < 48h** — janela de candidatura é diferencial competitivo real
4. **Seniority threshold relaxado** — empresas BR inflam requisitos (3-4 anos → "Verificar")
5. **Rastreamento de entrevistas por fonte** — para desligar o que não converte em 2 semanas
6. **Queries reposicionadas** — "Analista de Dados Jr" / "DBA Jr" em vez de "dev jr" genérico

---

## API endpoints

```
GET  /                              → UI (SPA)
GET  /api/jobs/search               → busca em todas as fontes (params: sort, show_ambiguous, brazil_only)
GET  /api/jobs/cache                → cache SQLite (instantâneo, sem APIs)
DEL  /api/jobs/cache                → limpa cache
POST /api/jobs/score                → score manual de uma vaga colada
GET  /api/jobs/keywords             → palavras-chave do perfil

GET  /api/kanban/                   → lista vagas no kanban
GET  /api/kanban/stats              → taxa de conversão por fonte
POST /api/kanban/add                → adiciona vaga
PATCH /api/kanban/{id}/move         → mover entre colunas
PATCH /api/kanban/{id}/notes        → atualizar notas
PATCH /api/kanban/{id}/interview    → toggle entrevista marcada
DEL  /api/kanban/{id}               → remover

GET  /api/answers/                  → respostas prontas (param: category)
GET  /api/answers/categories        → categorias

POST /api/cover-letter/generate     → gerar carta (body: title, company, description)
```

---

## Tabelas SQLite

### kanban_jobs
Vagas salvas pelo usuário no board kanban. Campos de rastreamento: `interview_scheduled`, `offer_received`, `applied_at`, `is_br`, `source` (para taxa de conversão por canal).

### collected_jobs
Cache de vagas coletadas das APIs. Atualizado a cada busca via upsert. Campos: `is_br`, `is_new`, `fit_score`, `seniority_score`, `seniority_label`, `level_signals`, `last_seen_at`.

---

## Como rodar

```bash
cd job_hunter
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # preencher chaves opcionais
uvicorn main:app --port 8000
# → http://localhost:8000
```

## Como adicionar nova fonte de vagas

1. Criar `collectors/nova_fonte.py` herdando de `BaseCollector`
2. Implementar `async def _fetch(self, queries) -> list[RawJob]`
3. Registrar em `collectors/registry.py` na lista `COLLECTORS`

---

## Testes

```bash
pytest tests/ -v   # 37 testes passando
```

Cobrem: blacklist de título (sr/pleno/lead/manager/architect), PL/SQL falso positivo, títulos mistos (Pleno/Júnior → ambíguo), regex de anos PT+EN, boundary em MAX_ALLOWED_YEARS, inject_junior_terms.

---

## Git history

```
586985a Apply LLM Council optimizations: Gupy, geo-filter, 48h badge, interview tracking
6f7914d Initial commit: Job Hunter — agregador de vagas júnior
```

---

## Recomendações pendentes (do conselho, não implementáveis via código)

1. **Reposicionar headline do LinkedIn** para "Analista de Dados Jr | SQL · Oracle · PL/SQL · Python · GCP" + ativar "Open to Work"
2. **Identificar 20 empresas-alvo** que usam Oracle/PL/SQL no Brasil e monitorar diretamente
3. **Atacar canal referral** — mensagem direta para devs sênior pedindo indicação interna
4. **Medir taxa de resposta** — após 2 semanas usando o rastreador de conversão, desligar fontes que não produzem entrevistas
5. **Auditar currículo** — pedir feedback de um recrutador real antes de otimizar mais código
