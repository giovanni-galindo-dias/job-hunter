"""
Busca vagas nas APIs externas e aplica o pipeline de filtragem de senioridade.
"""
import os
import hashlib
import re
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv

from services.matcher import score_fit
from services.seniority_filter import (
    compute_seniority,
    inject_junior_terms,
    AMBIGUOUS_MIN_SCORE,
    DEFAULT_MIN_SCORE,
)

load_dotenv()

SERPAPI_KEY   = os.getenv("SERPAPI_KEY", "")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

TIMEOUT = httpx.Timeout(15.0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_id(source: str, raw_id) -> str:
    return hashlib.md5(f"{source}:{raw_id}".encode()).hexdigest()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _build_job(
    *,
    source: str,
    raw_id,
    title: str,
    company: str,
    location: str,
    url: str,
    description: str,
    posted_at: str,
) -> dict:
    desc_clean = _strip_html(description)
    fit = score_fit(title, desc_clean)
    seniority = compute_seniority(title, desc_clean)

    return {
        "id": _make_id(source, raw_id),
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": desc_clean[:2000],
        "source": source,
        # scores separados
        "fit_score": fit["fit_score"],
        "matched_skills": fit["matched_skills"],
        "role_type": fit["role_type"],
        # senioridade
        "seniority_score": seniority.seniority_score,
        "seniority_label": seniority.seniority_label,
        "seniority_discard": seniority.discard,
        "level_signals": seniority.signals,
        "posted_at": posted_at,
    }


def _epoch_to_date(epoch) -> str:
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


# ── Fontes ────────────────────────────────────────────────────────────────────

async def fetch_remotive(keywords: list[str]) -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for kw in keywords[:4]:
            try:
                r = await client.get(
                    "https://remotive.com/api/remote-jobs",
                    params={"search": kw, "limit": 20},
                )
                if r.status_code != 200:
                    continue
                for job in r.json().get("jobs", []):
                    results.append(_build_job(
                        source="Remotive",
                        raw_id=job.get("id"),
                        title=job.get("title", ""),
                        company=job.get("company_name", ""),
                        location=job.get("candidate_required_location", "Remote"),
                        url=job.get("url", ""),
                        description=job.get("description", ""),
                        posted_at=job.get("publication_date", "")[:10],
                    ))
            except Exception:
                continue
    return results


async def fetch_remoteok(keywords: list[str]) -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for kw in keywords[:3]:
            try:
                tag = kw.split()[0].lower()
                r = await client.get(
                    "https://remoteok.com/api",
                    params={"tag": tag},
                    headers={"User-Agent": "JobHunterApp/1.0"},
                )
                if r.status_code != 200:
                    continue
                data = r.json()
                if isinstance(data, list):
                    data = data[1:]
                for job in data[:15]:
                    if not isinstance(job, dict):
                        continue
                    results.append(_build_job(
                        source="RemoteOK",
                        raw_id=job.get("id", ""),
                        title=job.get("position", ""),
                        company=job.get("company", ""),
                        location="Remote",
                        url=job.get("url", ""),
                        description=job.get("description", ""),
                        posted_at=_epoch_to_date(job.get("epoch", 0)),
                    ))
            except Exception:
                continue
    return results


async def fetch_adzuna(keywords: list[str]) -> list[dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
    results = []
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for kw in keywords[:3]:
            try:
                r = await client.get(
                    "https://api.adzuna.com/v1/api/jobs/br/search/1",
                    params={
                        "app_id": ADZUNA_APP_ID,
                        "app_key": ADZUNA_APP_KEY,
                        "what": kw,
                        "results_per_page": 15,
                        "content-type": "application/json",
                    },
                )
                if r.status_code != 200:
                    continue
                for job in r.json().get("results", []):
                    results.append(_build_job(
                        source="Adzuna",
                        raw_id=job.get("id", ""),
                        title=job.get("title", ""),
                        company=job.get("company", {}).get("display_name", ""),
                        location=job.get("location", {}).get("display_name", ""),
                        url=job.get("redirect_url", ""),
                        description=job.get("description", ""),
                        posted_at=job.get("created", "")[:10],
                    ))
            except Exception:
                continue
    return results


async def fetch_serpapi_google_jobs(keywords: list[str]) -> list[dict]:
    if not SERPAPI_KEY:
        return []
    results = []
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for kw in keywords[:3]:
            try:
                r = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_jobs",
                        "q": kw,
                        "hl": "pt",
                        "gl": "br",
                        "api_key": SERPAPI_KEY,
                    },
                )
                if r.status_code != 200:
                    continue
                for job in r.json().get("jobs_results", [])[:15]:
                    results.append(_build_job(
                        source="Google Jobs",
                        raw_id=job.get("job_id", ""),
                        title=job.get("title", ""),
                        company=job.get("company_name", ""),
                        location=job.get("location", ""),
                        url=job.get("share_link", ""),
                        description=job.get("description", ""),
                        posted_at=job.get("detected_extensions", {}).get("posted_at", ""),
                    ))
            except Exception:
                continue
    return results


# ── Pipeline principal ────────────────────────────────────────────────────────

async def fetch_all_jobs(
    keywords: list[str],
    show_ambiguous: bool = False,
) -> list[dict]:
    """
    Agrega todas as fontes, injeta termos junior nas queries (Camada 1),
    remove duplicatas e aplica o filtro de senioridade (Camadas 2-4).

    show_ambiguous=False → retorna apenas seniority_score >= DEFAULT_MIN_SCORE (50)
    show_ambiguous=True  → retorna também ambíguas (>= AMBIGUOUS_MIN_SCORE = 40)
    """
    # Camada 1: injeta "junior" nas queries
    enriched = [inject_junior_terms(kw) for kw in keywords]

    remotive  = await fetch_remotive(enriched)
    remoteok  = await fetch_remoteok(enriched)
    adzuna    = await fetch_adzuna(enriched)
    serpapi   = await fetch_serpapi_google_jobs(enriched)

    all_jobs = remotive + remoteok + adzuna + serpapi

    # Deduplicar por id
    seen: set[str] = set()
    unique: list[dict] = []
    for job in all_jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            unique.append(job)

    # Camadas 2-4: aplicar filtro de senioridade
    min_score = AMBIGUOUS_MIN_SCORE if show_ambiguous else DEFAULT_MIN_SCORE
    filtered = [j for j in unique if j["seniority_score"] >= min_score]

    # Ordenação: seniority_score DESC → fit_score DESC
    filtered.sort(key=lambda j: (j["seniority_score"], j["fit_score"]), reverse=True)

    return filtered
