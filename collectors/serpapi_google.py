"""
Google Jobs via SerpAPI — fonte mais importante.
Cada query bate no índice do Google que já agrega Gupy, LinkedIn,
Indeed, Vagas.com, InfoJobs, Catho e outros portais brasileiros.
Obtenha sua chave gratuita em: https://serpapi.com (100 req/mês)
"""
import os
import httpx
from dotenv import load_dotenv
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html
from collectors.query_builder import google_jobs_queries

load_dotenv()


class SerpAPIGoogleJobsCollector(BaseCollector):
    name = "Google Jobs"

    def __init__(self):
        self._key = os.getenv("SERPAPI_KEY", "")

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        if not self._key:
            raise RuntimeError("SERPAPI_KEY não configurada no .env")

        results: list[RawJob] = []
        queries = google_jobs_queries()    # queries otimizadas para BR

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for q in queries:
                # SerpAPI paginação via start=0,10,20...
                for start in [0, 10, 20]:
                    try:
                        r = await client.get(
                            "https://serpapi.com/search",
                            params={
                                "engine":  "google_jobs",
                                "q":       q,
                                "hl":      "pt",
                                "gl":      "br",
                                "start":   start,
                                "api_key": self._key,
                            },
                        )
                        if r.status_code != 200:
                            break
                        jobs_raw = r.json().get("jobs_results", [])
                        if not jobs_raw:
                            break
                        for job in jobs_raw:
                            ext = job.get("detected_extensions", {})
                            results.append(RawJob(
                                title=job.get("title", ""),
                                company=job.get("company_name", ""),
                                location=job.get("location", ""),
                                url=job.get("share_link", "") or job.get("apply_options", [{}])[0].get("link", ""),
                                description=strip_html(job.get("description", "")),
                                source=self.name,
                                external_id=job.get("job_id", ""),
                                posted_at=ext.get("posted_at", ""),
                                tags=[],
                            ))
                    except Exception:
                        break
        return results
