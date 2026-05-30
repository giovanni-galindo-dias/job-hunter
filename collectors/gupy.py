"""
Gupy — maior plataforma de RH do Brasil.
API pública: https://portal.api.gupy.io/api/v1/jobs
Parâmetro confirmado: jobName (sem "/" ou acentos)

BUGS CORRIGIDOS nesta versão:
  - Queries com "/" retornavam 0 → "PLSQL", "Oracle SQL"
  - Queries com acento retornavam 0 → sem acento
  - workplaceType: API retorna lowercase ("remote","hybrid") mas código
    comparava com uppercase → fix via case-insensitive
  - _search_companies removida: endpoint /api/job retorna 404 em
    todos os slugs testados → adicionado watchlist ao portal search
"""
import logging
import unicodedata
import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html

log = logging.getLogger("job_hunter.gupy")

# Queries testadas e confirmadas que retornam resultados.
# Regras:
#   - Sem "/" (PLSQL em vez de PL/SQL)
#   - Sem acentos (estagiario em vez de estagiário)
_GUPY_SEARCHES = [
    # ─ Banco de dados / SQL / PL/SQL ─────────────────
    "analista dados junior",
    "analista dados SQL",
    "desenvolvedor SQL junior",
    "Oracle junior",
    "PLSQL junior",
    "DBA junior",
    "banco de dados junior",
    # ─ Suporte / Service Desk ────────────────────────
    "analista suporte junior",
    "analista suporte tecnico junior",
    "service desk junior",
    "analista sustentacao junior",
    "helpdesk junior",
    # ─ Cloud / GCP ───────────────────────────────────
    "analista cloud junior",
    "cloud junior",
    "GCP junior",
    # ─ Backend / Python ──────────────────────────────
    "desenvolvedor python junior",
    "backend junior",
    # ─ Product Owner ─────────────────────────────────
    "product owner junior",
    "analista produto junior",
    # ─ Estágio / Trainee ─────────────────────────────
    "estagiario desenvolvimento",
    "estagiario TI",
    "trainee tecnologia",
    "estagiario banco dados",
    "estagiario suporte",
    # ─ Amplos ────────────────────────────────────────
    "analista junior",
    "desenvolvedor junior",
    "estagiario sistemas",
]


def _wtype_to_label(wtype: str, is_remote: bool, city: str, state: str) -> str:
    """Normaliza workplaceType (API retorna lowercase: 'remote','hybrid','on-site')."""
    wt = (wtype or "").lower()
    parts = [p for p in [city, state, "Brasil"] if p]
    loc = ", ".join(parts)
    if wt in ("remote", "remoto") or is_remote:
        return "Remoto (Brasil)"
    if wt in ("hybrid", "hibrido", "híbrido"):
        return f"Híbrido — {loc}"
    return loc


class GupyCollector(BaseCollector):
    name = "Gupy"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []
        seen_ids: set[str] = set()

        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        ) as client:
            for search in _GUPY_SEARCHES:
                query_count = 0
                for offset in [0, 40, 80]:
                    try:
                        r = await client.get(
                            "https://portal.api.gupy.io/api/v1/jobs",
                            params={"jobName": search, "limit": 40, "offset": offset},
                        )
                        if r.status_code != 200:
                            break

                        data = r.json()
                        jobs = data.get("data", [])
                        total_available = data.get("pagination", {}).get("total", 0)

                        if not jobs:
                            break

                        for job in jobs:
                            raw = self._parse_job(job)
                            if raw and raw.external_id not in seen_ids:
                                seen_ids.add(raw.external_id)
                                results.append(raw)
                                query_count += 1

                        # Não paginar além do disponível
                        if offset + 40 >= total_available:
                            break

                    except Exception as exc:
                        log.warning("[Gupy] query %r offset=%d erro: %s", search, offset, exc)
                        break

                if query_count:
                    log.debug("[Gupy] %r → %d vagas", search, query_count)

        log.info("[Gupy] total coletado: %d vagas únicas", len(results))
        return results

    def _parse_job(self, job: dict) -> RawJob | None:
        job_id = str(job.get("id", ""))
        if not job_id:
            return None

        city      = job.get("city", "") or ""
        state     = job.get("state", "") or ""
        wtype     = job.get("workplaceType", "") or ""
        is_remote = bool(job.get("isRemoteWork", False))
        location  = _wtype_to_label(wtype, is_remote, city, state)

        url = (
            job.get("jobUrl", "")
            or job.get("url", "")
            or f"https://www.gupy.io/vagas/{job_id}"
        )

        published = str(job.get("publishedDate", ""))[:10]

        return RawJob(
            title=job.get("name", "") or job.get("title", ""),
            company=job.get("careerPageName", "") or job.get("company", ""),
            location=location,
            url=url,
            description=strip_html(job.get("description", "")),
            source=self.name,
            external_id=job_id,
            posted_at=published,
            tags=[wtype] if wtype else [],
        )
