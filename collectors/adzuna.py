import logging
import os
import httpx
from dotenv import load_dotenv
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html
from collectors.query_builder import brazil_api_queries

load_dotenv()
log = logging.getLogger("job_hunter.adzuna")


class AdzunaCollector(BaseCollector):
    name = "Adzuna"

    def __init__(self):
        self._app_id  = os.getenv("ADZUNA_APP_ID", "")
        self._app_key = os.getenv("ADZUNA_APP_KEY", "")

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        if not self._app_id or not self._app_key:
            log.warning("[Adzuna] SKIPPED: ADZUNA_APP_ID/ADZUNA_APP_KEY ausentes no .env — "
                        "obtenha em https://developer.adzuna.com (250 req/dia grátis)")
            raise RuntimeError("ADZUNA_APP_ID / ADZUNA_APP_KEY não configuradas no .env")

        results: list[RawJob] = []
        searches = brazil_api_queries()[:8]

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for q in searches:
                for page in range(1, 4):   # 3 páginas por query
                    try:
                        r = await client.get(
                            f"https://api.adzuna.com/v1/api/jobs/br/search/{page}",
                            params={
                                "app_id": self._app_id,
                                "app_key": self._app_key,
                                "what": q,
                                "results_per_page": 20,
                                "content-type": "application/json",
                            },
                        )
                        if r.status_code != 200:
                            break
                        data = r.json().get("results", [])
                        if not data:
                            break
                        for job in data:
                            results.append(RawJob(
                                title=job.get("title", ""),
                                company=job.get("company", {}).get("display_name", ""),
                                location=job.get("location", {}).get("display_name", ""),
                                url=job.get("redirect_url", ""),
                                description=strip_html(job.get("description", "")),
                                source=self.name,
                                external_id=str(job.get("id", "")),
                                posted_at=str(job.get("created", ""))[:10],
                            ))
                    except Exception:
                        break
        return results
