import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html
from collectors.query_builder import remote_queries


class RemotiveCollector(BaseCollector):
    name = "Remotive"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []
        # Remotive não suporta query string multi-term bem; usa categories + search
        searches = remote_queries()[:6]
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for q in searches:
                try:
                    r = await client.get(
                        "https://remotive.com/api/remote-jobs",
                        params={"search": q, "limit": 20},
                    )
                    if r.status_code != 200:
                        continue
                    for job in r.json().get("jobs", []):
                        results.append(RawJob(
                            title=job.get("title", ""),
                            company=job.get("company_name", ""),
                            location=job.get("candidate_required_location", "Remote"),
                            url=job.get("url", ""),
                            description=strip_html(job.get("description", "")),
                            source=self.name,
                            external_id=str(job.get("id", "")),
                            posted_at=str(job.get("publication_date", ""))[:10],
                            tags=job.get("tags", []),
                        ))
                except Exception:
                    continue
        return results
