"""
The Muse API — filtro nativo entry level. API gratuita, sem chave.
https://www.themuse.com/developers/api/v2

CORRIGIDO: category param retornava 0 resultados pois os nomes não batiam
com os valores aceitos pela API. Agora usa apenas level=Entry Level (global)
e filtra por keywords no título pós-coleta.
"""
import logging
import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html

log = logging.getLogger("job_hunter.themuse")

# Keywords para filtrar títulos relevantes ao perfil pós-coleta
_RELEVANT_KEYWORDS = [
    "sql", "oracle", "database", "data analyst", "data engineer",
    "support", "cloud", "gcp", "python", "backend", "product owner",
    "helpdesk", "service desk", "junior", "entry", "analyst",
    "plsql", "pl/sql", "bi ", "bi,", "analytics",
]


class TheMuseCollector(BaseCollector):
    name = "The Muse"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []
        total_fetched = 0

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for page in range(1, 6):   # 5 páginas × 20 = até 100 vagas entry-level
                try:
                    r = await client.get(
                        "https://www.themuse.com/api/public/jobs",
                        params={
                            "level": "Entry Level",
                            "page":  page,
                        },
                    )
                    if r.status_code != 200:
                        log.warning("[The Muse] HTTP %d na page %d", r.status_code, page)
                        break

                    data = r.json()
                    jobs_raw = data.get("results", [])
                    if not jobs_raw:
                        break

                    total_fetched += len(jobs_raw)

                    for job in jobs_raw:
                        title = job.get("name", "").lower()
                        # Filtra por relevância ao perfil
                        if not any(kw in title for kw in _RELEVANT_KEYWORDS):
                            continue

                        locs = job.get("locations", [{}])
                        location = locs[0].get("name", "") if locs else ""

                        results.append(RawJob(
                            title=job.get("name", ""),
                            company=job.get("company", {}).get("name", ""),
                            location=location,
                            url=job.get("refs", {}).get("landing_page", ""),
                            description=strip_html(job.get("contents", "")),
                            source=self.name,
                            external_id=str(job.get("id", "")),
                            posted_at=str(job.get("publication_date", ""))[:10],
                            tags=["Entry Level"],
                        ))

                except Exception as exc:
                    log.warning("[The Muse] erro na page %d: %s", page, exc)
                    break

        log.info("[The Muse] fetched=%d relevant=%d", total_fetched, len(results))
        return results
