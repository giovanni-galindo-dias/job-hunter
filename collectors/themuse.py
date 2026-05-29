"""
The Muse API — tem filtro nativo de nível "entry level". API gratuita sem chave.
https://www.themuse.com/developers/api/v2
"""
import httpx
from collectors.base import BaseCollector, RawJob, TIMEOUT, strip_html
from collectors.query_builder import themuse_categories


class TheMuseCollector(BaseCollector):
    name = "The Muse"

    async def _fetch(self, _queries: list[str]) -> list[RawJob]:
        results: list[RawJob] = []
        categories = themuse_categories()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for cat in categories:
                for page in range(1, 4):
                    try:
                        r = await client.get(
                            "https://www.themuse.com/api/public/jobs",
                            params={
                                "category": cat,
                                "level":    "Entry Level",
                                "page":     page,
                            },
                        )
                        if r.status_code != 200:
                            break
                        data = r.json()
                        jobs_raw = data.get("results", [])
                        if not jobs_raw:
                            break
                        for job in jobs_raw:
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
                                tags=[cat],
                            ))
                    except Exception:
                        break
        return results
