"""
Arbeitnow — vagas remotas e internacionais, API gratuita sem chave.
https://www.arbeitnow.com/api/job-board-api
"""
import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html, epoch_to_date
from collectors.query_builder import remote_queries


class ArbeitnowCollector(BaseCollector):
    name = "Arbeitnow"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []
        tags_map = {
            "python": "python",
            "sql": "sql",
            "cloud": "cloud",
            "junior": "junior",
            "data": "data-analyst",
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Busca geral + por tag
            endpoints = [
                "https://www.arbeitnow.com/api/job-board-api",
            ]
            for tag in ["python", "sql", "junior"]:
                endpoints.append(f"https://www.arbeitnow.com/api/job-board-api?tags={tag}")

            for url in endpoints:
                try:
                    for page in range(1, 4):
                        r = await client.get(url + ("&" if "?" in url else "?") + f"page={page}")
                        if r.status_code != 200:
                            break
                        data = r.json().get("data", [])
                        if not data:
                            break
                        for job in data:
                            results.append(RawJob(
                                title=job.get("title", ""),
                                company=job.get("company_name", ""),
                                location=job.get("location", "Remote"),
                                url=job.get("url", ""),
                                description=strip_html(job.get("description", "")),
                                source=self.name,
                                external_id=str(job.get("slug", "")),
                                posted_at=epoch_to_date(job.get("created_at", 0)),
                                tags=job.get("tags", []),
                            ))
                except Exception:
                    continue
        return results
