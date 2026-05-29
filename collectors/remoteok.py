import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, UA, epoch_to_date, strip_html
from collectors.query_builder import tag_queries


class RemoteOKCollector(BaseCollector):
    name = "RemoteOK"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []
        tags = tag_queries()
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=UA) as client:
            for tag in tags[:5]:
                try:
                    r = await client.get(
                        "https://remoteok.com/api",
                        params={"tag": tag},
                    )
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    if isinstance(data, list) and data:
                        data = data[1:]   # primeiro elemento é metadado
                    for job in data[:20]:
                        if not isinstance(job, dict):
                            continue
                        results.append(RawJob(
                            title=job.get("position", ""),
                            company=job.get("company", ""),
                            location="Remote",
                            url=job.get("url", ""),
                            description=strip_html(job.get("description", "")),
                            source=self.name,
                            external_id=str(job.get("id", "")),
                            posted_at=epoch_to_date(job.get("epoch", 0)),
                            tags=job.get("tags", []) if isinstance(job.get("tags"), list) else [],
                        ))
                except Exception:
                    continue
        return results
