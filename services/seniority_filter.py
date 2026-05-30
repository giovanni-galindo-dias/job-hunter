"""
Filtragem de senioridade em 4 camadas.

Edite as constantes abaixo para ajustar o comportamento do filtro
sem precisar alterar a lógica principal.

  CAMADA 1 — inject_junior_terms():   injeta termos júnior nas queries
  CAMADA 2 — check_title_seniority(): blacklist de palavras no título
  CAMADA 3 — analyze_description():   regex de anos e sinais de nível
  CAMADA 4 — compute_seniority():     SENIORITY_SCORE final (0–100)
"""

import re
from typing import NamedTuple

# ── Constantes editáveis ──────────────────────────────────────────────────────

# Camada 1 — sufixos injetados nas queries quando nenhum nível é detectado
JUNIOR_QUERY_SUFFIXES = [
    "junior", "júnior", "jr", "trainee", "entry level", "estágio",
]

# Camada 2 — termos no TÍTULO que indicam nível sênior → DESCARTE
# Cada item é um padrão regex (case-insensitive, word boundaries aplicados)
BLACKLIST_TITLE_PATTERNS: list[str] = [
    r"senior",
    r"s[eê]nior",
    r"sr\.?",                          # "Dev Sr" ou "Sr."
    r"pleno",
    r"pl\.?(?!\s*/\s*sql)",            # "Analista Pl" mas NÃO "PL/SQL"
    r"specialist",
    r"especialista",
    r"lead",
    r"l[ií]der",
    r"principal",
    r"staff",
    r"manager",
    r"gerente",
    r"coordenador[a]?",
    r"coordinator",
    r"head",
    r"architect",
    r"arquiteto[a]?",
    r"expert",
    r"tech\s*lead",
    r"supervisor[a]?",
    r"iii",                            # nível III+
    r"iv",
    r"ii",                             # nível II (pleno na maioria das empresas)
]

# Camada 2 — termos no TÍTULO que confirmam júnior → bônus
JUNIOR_TITLE_PATTERNS: list[str] = [
    r"j[uú]nior",
    r"jr\.?",
    r"trainee",
    r"estagi[aá]ri[oa]",
    r"est[aá]gio",
    r"entry[\s\-]level",
    r"aprendiz",
    r"\bi\b",                          # "Analista I" = nível 1 (júnior)
]

# Camada 3 — padrões para extrair anos de experiência exigidos
YEARS_REQ_PATTERNS: list[str] = [
    r"(\d+)\s*\+?\s*anos?\s+de\s+experi[eê]ncia",
    r"m[íi]nimo\s+de\s+(\d+)\s+anos?",
    r"acima\s+de\s+(\d+)\s+anos?",
    r"pelo\s+menos\s+(\d+)\s+anos?",
    r"(\d+)\s+a\s+\d+\s+anos?\s+de\s+experi[eê]ncia",
    r"(\d+)\+\s*years?\s+of\s+experience",
    r"(\d+)\+\s*years?",
    r"minimum\s+of\s+(\d+)\s+years?",
    r"at\s+least\s+(\d+)\s+years?",
    r"(\d+)\s+to\s+\d+\s+years?\s+of\s+experience",
]

# Camada 3 — sinais positivos de júnior na descrição
JUNIOR_DESC_PATTERNS: list[str] = [
    r"in[íi]cio\s+de\s+carreira",
    r"rec[eé]m[\s\-]formad[oa]",
    r"primeira\s+experi[eê]ncia",
    r"sem\s+experi[eê]ncia\s+(pr[eé]via|necess[aá]ria)?",
    r"buscamos\s+j[uú]nior",
    r"em\s+forma[çc][aã]o",
    r"estar(?:emos)?\s+formand[oa]",
    r"plano\s+de\s+desenvolvimento",
    r"trainee",
    r"entry[\s\-]level",
    r"aprendiz",
    r"jovem\s+talento",
    r"0\s*[-a]\s*[12]\s+anos?",
    r"at[eé]\s+[12]\s+anos?\s+de\s+experi[eê]ncia",
    r"no\s+experience\s+required",
]

# Camada 4 — limiares de anos de experiência
# ATUALIZAÇÃO (veredicto do conselho): empresas brasileiras escrevem requisitos
# inflados — "2-3 anos" em vaga júnior é comum e negociável.
# Threshold relaxado: > 4 anos → descarte; 3-4 anos → "Verificar" (score 40)
MAX_ALLOWED_YEARS = 4       # vagas que exigem > 4 anos → descarte
VERIFY_YEARS_THRESHOLD = 3  # vagas com 3-4 anos exigidos → verificar manualmente
AMBIGUOUS_MIN_SCORE = 40    # score mínimo para toggle "mostrar ambíguas"
DEFAULT_MIN_SCORE = 50      # score mínimo na exibição padrão


# ── Compilar regex ────────────────────────────────────────────────────────────

def _compile(patterns: list[str]) -> re.Pattern:
    return re.compile(
        "|".join(rf"(?:{p})" for p in patterns),
        re.IGNORECASE,
    )


_BLACKLIST_RE = _compile([rf"\b{p}\b" for p in BLACKLIST_TITLE_PATTERNS])
_JUNIOR_TITLE_RE = _compile([rf"\b{p}\b" for p in JUNIOR_TITLE_PATTERNS])
_YEARS_RE = [re.compile(p, re.IGNORECASE) for p in YEARS_REQ_PATTERNS]
_JUNIOR_DESC_RE = _compile(JUNIOR_DESC_PATTERNS)


# ── Camada 1 ──────────────────────────────────────────────────────────────────

def inject_junior_terms(keyword: str) -> str:
    """
    Adiciona 'junior' à keyword se não houver indicador de nível.
    Evita duplicar se o usuário já incluiu 'senior', 'pleno', etc.
    """
    kw_lower = keyword.lower()
    all_indicators = JUNIOR_QUERY_SUFFIXES + [
        "senior", "sênior", "pleno", "specialist", "lead",
    ]
    if any(ind in kw_lower for ind in all_indicators):
        return keyword
    return f"{keyword} junior"


# ── Camada 2 ──────────────────────────────────────────────────────────────────

def check_title_seniority(title: str) -> dict:
    """
    Classifica o título em 'junior', 'senior' ou 'ambiguous'.

    Returns:
        status:        "junior" | "senior" | "ambiguous"
        blacklist_hits: termos de blacklist encontrados
        junior_hits:    termos de júnior encontrados
    """
    blacklist_hits = [m.group() for m in _BLACKLIST_RE.finditer(title)]
    junior_hits = [m.group() for m in _JUNIOR_TITLE_RE.finditer(title)]

    if blacklist_hits and not junior_hits:
        return {"status": "senior", "blacklist_hits": blacklist_hits, "junior_hits": []}

    if blacklist_hits and junior_hits:
        # Ambos presentes → ex: "Analista Pleno/Júnior"
        return {"status": "ambiguous", "blacklist_hits": blacklist_hits, "junior_hits": junior_hits}

    if junior_hits:
        return {"status": "junior", "blacklist_hits": [], "junior_hits": junior_hits}

    # Nenhum sinal → ambíguo por omissão
    return {"status": "ambiguous", "blacklist_hits": [], "junior_hits": []}


# ── Camada 3 ──────────────────────────────────────────────────────────────────

def analyze_description(description: str) -> dict:
    """
    Extrai exigência de anos e sinais positivos de júnior da descrição.

    Returns:
        required_years:  int | None  — máximo de anos detectado
        years_text:      str | None  — trecho original
        junior_signals:  list[str]   — expressões de júnior encontradas
        discard:         bool        — True se exige > MAX_ALLOWED_YEARS
    """
    found_years: list[int] = []
    years_texts: list[str] = []

    for pat in _YEARS_RE:
        for m in pat.finditer(description):
            try:
                found_years.append(int(m.group(1)))
                years_texts.append(m.group(0).strip())
            except (IndexError, ValueError):
                pass

    required_years = max(found_years) if found_years else None
    discard = required_years is not None and required_years > MAX_ALLOWED_YEARS

    junior_signals = [m.group() for m in _JUNIOR_DESC_RE.finditer(description)]
    # Deduplica mantendo ordem
    seen: set[str] = set()
    unique_signals: list[str] = []
    for s in junior_signals:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique_signals.append(s)

    # Vagas com 3-4 anos no Brasil costumam ser negociáveis — marca como "verificar"
    needs_verify = (
        required_years is not None
        and VERIFY_YEARS_THRESHOLD <= required_years <= MAX_ALLOWED_YEARS
    )

    return {
        "required_years": required_years,
        "years_text": years_texts[0] if years_texts else None,
        "junior_signals": unique_signals,
        "discard": discard,
        "needs_verify": needs_verify,
    }


# ── Camada 4 ──────────────────────────────────────────────────────────────────

class SeniorityResult(NamedTuple):
    seniority_score: int    # 0-100
    seniority_label: str    # "Júnior" | "Ambíguo" | "Sênior/Pleno"
    discard: bool           # True = filtrar por padrão
    signals: list[str]      # sinais coletados para exibição no card


def compute_seniority(title: str, description: str) -> SeniorityResult:
    """
    Combina as camadas 2 e 3 para produzir o SENIORITY_SCORE.

    Escala:
      100 = explicitamente júnior + sinais positivos na descrição
       80 = explicitamente júnior (título), descrição neutra
       70 = implicitamente júnior (sem sinais sênior), sinais positivos
       50 = implicitamente júnior, descrição neutra
       40 = ambíguo (título misto ou sem nível, sem sinais positivos)
        0 = sênior/pleno no título OU exigência de anos > MAX_ALLOWED_YEARS
    """
    title_result = check_title_seniority(title)
    desc_result = analyze_description(description)
    signals: list[str] = []

    # ── Caso de descarte ──────────────────────────────────────────────────────
    if desc_result["discard"]:
        yr = desc_result["required_years"]
        signals.append(f"exige {yr} anos")
        return SeniorityResult(0, "Sênior/Pleno", True, signals)

    if title_result["status"] == "senior":
        signals.extend(title_result["blacklist_hits"])
        return SeniorityResult(0, "Sênior/Pleno", True, signals)

    # ── Vagas "Verificar": 3-4 anos exigidos (negociáveis no Brasil) ──────────
    if desc_result.get("needs_verify"):
        yr = desc_result["required_years"]
        signals.append(f"⚠ exige {yr} anos — verifique se negociável")
        if title_result["status"] == "junior":
            signals.extend(title_result["junior_hits"])
            return SeniorityResult(55, "Verificar", False, signals)
        return SeniorityResult(40, "Verificar", False, signals)

    # ── Calcular bônus de júnior ─────────────────────────────────────────────
    desc_bonus = 0
    if desc_result["junior_signals"]:
        desc_bonus += 15
        signals.extend(desc_result["junior_signals"][:3])  # exibe até 3 sinais

    if desc_result["required_years"] is not None:
        yr = desc_result["required_years"]
        if yr <= 1:
            desc_bonus += 10
            signals.append(f"exige {yr} ano")
        elif yr <= 2:
            desc_bonus += 5
            signals.append(f"exige {yr} anos")

    # ── Classificar ──────────────────────────────────────────────────────────
    if title_result["status"] == "junior":
        signals.extend(title_result["junior_hits"])
        score = min(100, 80 + desc_bonus)
        return SeniorityResult(score, "Júnior", False, signals)

    if title_result["status"] == "ambiguous":
        if title_result["junior_hits"]:
            signals.extend(title_result["junior_hits"])
        if title_result["blacklist_hits"]:
            signals.extend(title_result["blacklist_hits"])
        score = min(70, 40 + desc_bonus)
        return SeniorityResult(score, "Ambíguo", False, signals)

    # Fallback
    return SeniorityResult(50, "Ambíguo", False, signals)
