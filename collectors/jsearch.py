"""
JSearch via RapidAPI — agrega LinkedIn, Indeed, Glassdoor e outros.
Chave gratuita (200 req/mês): https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
Configure JSEARCH_API_KEY no .env.
"""
import logging
import os
import httpx
from dotenv import load_dotenv
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html
from collectors.query_builder import brazil_api_queries

load_dotenv()
log = logging.getLogger("job_hunter.jsearch")


class JSearchCollector(BaseCollector):
    name = "JSearch"

    def __init__(self):
        self._key = os.getenv("JSEARCH_API_KEY", "")

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        if not self._key:
            log.warning("[JSearch] SKIPPED: JSEARCH_API_KEY ausente no .env — "
                        "obtenha em https://rapidapi.com (200 req/mês grátis)")
            raise RuntimeError("JSEARCH_API_KEY não configurada no .env")

        results: list[RawJob] = []
        searches = brazil_api_queries()[:6]
        headers = {
            "X-RapidAPI-Key":  self._key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            for q in searches:
                for page in range(1, 4):
                    try:
                        r = await client.get(
                            "https://jsearch.p.rapidapi.com/search",
                            params={
                                "query":             f"{q} Brasil",
                                "page":              page,
                                "num_pages":         1,
                                "date_posted":       "month",
                                "employment_types":  "FULLTIME,PARTTIME,INTERN",
                            },
                        )
                        if r.status_code != 200:
                            break
                        data = r.json().get("data", [])
                        if not data:
                            break
                        for job in data:
                            results.append(RawJob(
                                title=job.get("job_title", ""),
                                company=job.get("employer_name", ""),
                                location=f"{job.get('job_city','')}, {job.get('job_country','')}".strip(", "),
                                url=job.get("job_apply_link", "") or job.get("job_google_link", ""),
                                description=strip_html(job.get("job_description", "")),
                                source=self.name,
                                external_id=job.get("job_id", ""),
                                posted_at=str(job.get("job_posted_at_datetime_utc", ""))[:10],
                                tags=job.get("job_required_skills", []) or [],
                            ))
                    except Exception:
                        break
        return results
