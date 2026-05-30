"""
Gupy — maior plataforma de RH do Brasil.
Usada por 80%+ das empresas médias/grandes. API pública, sem chave.
https://portal.api.gupy.io/api/v1/jobs
"""
import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html

# Queries específicas para o mercado brasileiro via Gupy
_GUPY_SEARCHES = [
    "PL/SQL junior",
    "Oracle junior",
    "analista suporte junior",
    "analista sustentação junior",
    "service desk junior",
    "analista dados junior",
    "analista dados SQL",
    "cloud GCP junior",
    "desenvolvedor python junior",
    "product owner junior",
    "DBA junior",
    "estagiário desenvolvimento sistemas",
    "trainee TI tecnologia",
    "estagiário banco de dados",
    "analista suporte técnico junior",
]

_WORKPLACE = ["REMOTE", "HYBRID", "ON_SITE"]  # busca em todos os modelos


class GupyCollector(BaseCollector):
    name = "Gupy"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []

        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        ) as client:
            for search in _GUPY_SEARCHES:
                for offset in [0, 40, 80]:   # 3 páginas × 40 = até 120 por query
                    try:
                        r = await client.get(
                            "https://portal.api.gupy.io/api/v1/jobs",
                            params={
                                "jobName": search,
                                "limit":   40,
                                "offset":  offset,
                            },
                        )
                        if r.status_code != 200:
                            break

                        data = r.json()
                        jobs = data.get("data", [])
                        if not jobs:
                            break

                        for job in jobs:
                            city  = job.get("city", "") or ""
                            state = job.get("state", "") or ""
                            loc   = ", ".join(p for p in [city, state, "Brasil"] if p)
                            wtype = job.get("workplaceType", "")
                            if wtype == "REMOTE":
                                loc = "Remoto (Brasil)"
                            elif wtype == "HYBRID":
                                loc = f"Híbrido — {loc}"

                            results.append(RawJob(
                                title=job.get("name", ""),
                                company=job.get("careerPageName", ""),
                                location=loc,
                                url=(
                                    job.get("jobUrl", "")
                                    or f"https://www.gupy.io/vagas/{job.get('id', '')}"
                                ),
                                description=strip_html(job.get("description", "")),
                                source=self.name,
                                external_id=str(job.get("id", "")),
                                posted_at=str(job.get("publishedDate", ""))[:10],
                                tags=[wtype] if wtype else [],
                            ))

                    except Exception:
                        break  # falha isolada — continua para próxima query

        return results
