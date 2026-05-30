"""
Gupy — maior plataforma de RH do Brasil.
Usada por 80%+ das empresas médias/grandes. API pública, sem chave.

Endpoint confirmado: https://portal.api.gupy.io/api/v1/jobs
Parâmetro: jobName (obrigatório), limit, offset

BUGS CORRIGIDOS:
- "PL/SQL junior" retornava 0 porque "/" quebra a busca → usar "PLSQL" ou "SQL Oracle"
- workplaceType comprado com "REMOTE"/"HYBRID" (maiúsculo) mas API retorna
  "remote"/"hybrid"/"on-site" → comparação agora é case-insensitive
- Queries com acento (estagiário, sustentação) retornavam 0 → versões sem acento
- description vazia na listagem: o campo existe mas pode estar vazio em vagas antigas
"""
import logging
import unicodedata
import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html

log = logging.getLogger("job_hunter.gupy")

# Queries testadas e confirmadas que retornam resultados na API Gupy.
# Regras aprendidas empiricamente:
#   - Sem "/" (PL/SQL → "PLSQL" ou "Oracle SQL")
#   - Sem acentos (estagiário → estagiario)
#   - Termos compostos com espaço funcionam bem
_GUPY_SEARCHES = [
    # Banco de dados / SQL / PL/SQL
    "analista dados junior",
    "analista dados SQL",
    "desenvolvedor SQL junior",
    "Oracle junior",
    "PLSQL junior",
    "DBA junior",
    "banco de dados junior",
    # Suporte / Service Desk
    "analista suporte junior",
    "analista suporte tecnico junior",
    "service desk junior",
    "analista sustentacao junior",
    "helpdesk junior",
    # Cloud / GCP
    "analista cloud junior",
    "cloud junior",
    "GCP junior",
    # Backend / Python
    "desenvolvedor python junior",
    "backend junior",
    # Product Owner
    "product owner junior",
    "analista produto junior",
    # Estágio / Trainee
    "estagiario desenvolvimento",
    "estagiario TI",
    "trainee tecnologia",
    "estagiario banco dados",
    "estagiario suporte",
    # Termos amplos para volume
    "analista junior",
    "desenvolvedor junior",
    "estagiario sistemas",
]

# Empresas-alvo que usam Oracle/PL/SQL no Brasil — consultadas diretamente.
# Adicione mais em profile.py → "gupy_target_companies".
_TARGET_COMPANIES = [
    "totvs",
    "bradesco",
    "itau",
    "santander",
    "bb-tecnologia-e-servicos",
    "claro",
    "vivo",
    "embraer",
    "ambev",
    "magazine-luiza",
]


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _wtype_to_label(wtype: str, is_remote: bool, city: str, state: str) -> str:
    """
    Normaliza workplaceType (API retorna lowercase: 'remote', 'hybrid', 'on-site').
    """
    wt = (wtype or "").lower()
    if wt in ("remote", "remoto") or is_remote:
        return "Remoto (Brasil)"
    parts = [p for p in [city, state, "Brasil"] if p]
    loc = ", ".join(parts)
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
                "Accept":     "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        ) as client:
            results += await self._search_all(client, seen_ids)
            results += await self._search_companies(client, seen_ids)

        log.info("[Gupy] total coletado: %d vagas", len(results))
        return results

    async def _search_all(self, client: httpx.AsyncClient, seen_ids: set) -> list[RawJob]:
        """Busca por termo no portal público Gupy."""
        results: list[RawJob] = []
        for search in _GUPY_SEARCHES:
            query_total = 0
            for offset in [0, 40, 80]:
                try:
                    r = await client.get(
                        "https://portal.api.gupy.io/api/v1/jobs",
                        params={"jobName": search, "limit": 40, "offset": offset},
                    )
                    if r.status_code != 200:
                        log.debug("[Gupy] %r offset=%d → HTTP %d", search, offset, r.status_code)
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
                            query_total += 1

                    # Não paginar além do total disponível
                    if offset + 40 >= total_available:
                        break

                except Exception as exc:
                    log.warning("[Gupy] erro em query %r: %s", search, exc)
                    break  # vai para próxima query

            if query_total:
                log.debug("[Gupy] %r → %d vagas", search, query_total)

        return results

    async def _search_companies(self, client: httpx.AsyncClient, seen_ids: set) -> list[RawJob]:
        """
        Consulta diretamente as páginas de carreira de empresas-alvo.
        Ex: https://totvs.gupy.io/api/job?jobName=junior
        """
        results: list[RawJob] = []
        for slug in _TARGET_COMPANIES:
            for search in ["junior", "estagiario", "trainee", "dados", "suporte", "SQL"]:
                try:
                    r = await client.get(
                        f"https://{slug}.gupy.io/api/job",
                        params={"jobName": search, "limit": 20},
                    )
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    # API de portal retorna lista direta ou dict com jobs
                    job_list = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
                    for job in job_list:
                        raw = self._parse_job(job, source_company=slug)
                        if raw and raw.external_id not in seen_ids:
                            seen_ids.add(raw.external_id)
                            results.append(raw)
                except Exception:
                    pass  # empresa-alvo inacessível — continua

        if results:
            log.info("[Gupy] empresas-alvo → %d vagas extras", len(results))
        return results

    def _parse_job(self, job: dict, source_company: str = "") -> RawJob | None:
        """Converte um job dict da API Gupy em RawJob."""
        job_id = str(job.get("id", ""))
        if not job_id:
            return None

        city  = job.get("city", "") or ""
        state = job.get("state", "") or ""
        wtype = job.get("workplaceType", "") or ""
        is_remote = bool(job.get("isRemoteWork", False))

        location = _wtype_to_label(wtype, is_remote, city, state)

        # jobUrl pode estar ausente em resultados de portal direto
        url = (
            job.get("jobUrl", "")
            or job.get("url", "")
            or f"https://www.gupy.io/vagas/{job_id}"
        )

        published = (
            str(job.get("publishedDate", ""))
            or str(job.get("updatedAt", ""))
        )[:10]

        return RawJob(
            title=job.get("name", "") or job.get("title", ""),
            company=job.get("careerPageName", "") or job.get("company", source_company),
            location=location,
            url=url,
            description=strip_html(job.get("description", "")),
            source=self.name,
            external_id=job_id,
            posted_at=published,
            tags=[wtype] if wtype else [],
        )
