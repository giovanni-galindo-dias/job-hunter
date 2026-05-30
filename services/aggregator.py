"""
Orquestrador central de vagas.

Pipeline:
  1. Executa todos os coletores em PARALELO (asyncio.gather).
  2. Achata os resultados em uma lista única.
  3. Deduplica por (título normalizado, empresa normalizada).
  4. Geo-filter opcional: prioriza ou restringe a vagas no Brasil.
  5. Aplica filtragem de senioridade (4 camadas).
  6. Calcula fit_score e seniority_score.
  7. Marca vagas com menos de 48h como "is_new" (prioridade de candidatura).
  8. Persiste no cache SQLite (upsert por id).
  9. Retorna vagas + estatísticas por fonte.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from collectors.registry import COLLECTORS, BR_NATIVE_SOURCES
from collectors.base import RawJob, CollectorResult
from models import CollectedJob
from services.matcher import score_fit
from services.seniority_filter import compute_seniority, DEFAULT_MIN_SCORE, AMBIGUOUS_MIN_SCORE


# ── Geo-filter ────────────────────────────────────────────────────────────────

_BR_LOCATION_KW = {
    "brasil", "brazil", "br", "são paulo", "sp", "rio de janeiro", "rj",
    "minas gerais", "mg", "belo horizonte", "porto alegre", "curitiba",
    "salvador", "recife", "fortaleza", "guaratinguetá", "campinas",
    "remoto", "remote", "híbrido", "hybrid",
}


def _is_brazil_job(source: str, location: str) -> bool:
    """True se a vaga é de fonte BR nativa ou a localização indica Brasil."""
    if source in BR_NATIVE_SOURCES:
        return True
    loc = location.lower()
    return any(kw in loc for kw in _BR_LOCATION_KW)


# ── 48h detector ─────────────────────────────────────────────────────────────

def _is_recent(posted_at: str) -> bool:
    """True se a vaga foi publicada nas últimas 48 horas."""
    if not posted_at:
        return False
    try:
        posted = datetime.strptime(posted_at[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - posted) <= timedelta(hours=48)
    except Exception:
        return False


# ── Deduplicação ──────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {
    "Gupy":       1,  # BR #1
    "Google Jobs":2,
    "Adzuna":     3,
    "JSearch":    4,
    "Remotive":   5,
    "RemoteOK":   6,
    "Arbeitnow":  7,
    "The Muse":   8,
}


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _dedup(jobs: list[RawJob]) -> list[RawJob]:
    """Mantém uma vaga por (título_norm, empresa_norm), preferindo fonte de maior prioridade."""
    seen: dict[tuple, RawJob] = {}
    for job in jobs:
        key = (_norm(job.title), _norm(job.company))
        if key in seen:
            existing_prio = _SOURCE_PRIORITY.get(seen[key].source, 99)
            new_prio = _SOURCE_PRIORITY.get(job.source, 99)
            if new_prio < existing_prio:
                seen[key] = job
        else:
            seen[key] = job
    return list(seen.values())


# ── Pipeline principal ────────────────────────────────────────────────────────

async def aggregate_jobs(
    show_ambiguous: bool = False,
    brazil_only: bool = False,
    db: Session | None = None,
) -> dict:
    """
    Coleta vagas de todas as fontes em paralelo, filtra e retorna.

    brazil_only=True → descarta vagas sem localização BR (exceto fontes nativas BR)
    """
    tasks = [c.collect([]) for c in COLLECTORS]
    results: list[CollectorResult] = await asyncio.gather(*tasks)

    all_raw: list[RawJob] = []
    source_stats: dict[str, dict] = {}
    for res in results:
        source_stats[res.name] = {
            "collected": len(res.jobs),
            "error": res.error,
            "is_br": res.name in BR_NATIVE_SOURCES,
        }
        all_raw.extend(res.jobs)

    total_collected = len(all_raw)

    # Geo-filter (opcional)
    if brazil_only:
        all_raw = [j for j in all_raw if _is_brazil_job(j.source, j.location)]

    # Deduplicação
    unique = _dedup(all_raw)
    total_deduped = len(unique)

    # Score + filtro de senioridade
    min_score = AMBIGUOUS_MIN_SCORE if show_ambiguous else DEFAULT_MIN_SCORE
    processed: list[dict] = []
    for raw in unique:
        seniority = compute_seniority(raw.title, raw.description)
        if seniority.seniority_score < min_score:
            continue
        fit = score_fit(raw.title, raw.description)
        is_br = _is_brazil_job(raw.source, raw.location)
        is_new = _is_recent(raw.posted_at)

        processed.append({
            "id":               raw.job_id,
            "title":            raw.title,
            "company":          raw.company,
            "location":         raw.location,
            "url":              raw.url,
            "description":      raw.description[:2000],
            "source":           raw.source,
            "posted_at":        raw.posted_at,
            "is_br":            is_br,
            "is_new":           is_new,
            "fit_score":        fit["fit_score"],
            "matched_skills":   fit["matched_skills"],
            "role_type":        fit["role_type"],
            "seniority_score":  seniority.seniority_score,
            "seniority_label":  seniority.seniority_label,
            "level_signals":    seniority.signals,
        })

    total_filtered = len(processed)

    # Ordenação: novas BR primeiro → seniority DESC → fit DESC
    processed.sort(
        key=lambda j: (
            j["is_new"],       # novas primeiro
            j["is_br"],        # BR primeiro
            j["seniority_score"],
            j["fit_score"],
        ),
        reverse=True,
    )

    if db is not None:
        _upsert_cache(processed, db)

    return {
        "jobs":            processed,
        "source_stats":    source_stats,
        "total_collected": total_collected,
        "total_deduped":   total_deduped,
        "total_filtered":  total_filtered,
    }


def load_from_cache(
    db: Session,
    show_ambiguous: bool = False,
    brazil_only: bool = False,
    sort: str = "seniority",
) -> dict | None:
    min_score = AMBIGUOUS_MIN_SCORE if show_ambiguous else DEFAULT_MIN_SCORE
    q = db.query(CollectedJob).filter(CollectedJob.seniority_score >= min_score)
    if brazil_only:
        q = q.filter(CollectedJob.is_br == True)
    rows = q.all()
    if not rows:
        return None

    jobs = [_row_to_dict(r) for r in rows]
    _sort_jobs(jobs, sort)

    source_counts: dict[str, dict] = {}
    for j in jobs:
        src = j["source"]
        if src not in source_counts:
            source_counts[src] = {"collected": 0, "error": None, "is_br": j.get("is_br", False)}
        source_counts[src]["collected"] += 1

    return {
        "jobs":            jobs,
        "source_stats":    source_counts,
        "total_collected": len(jobs),
        "total_deduped":   len(jobs),
        "total_filtered":  len(jobs),
        "from_cache":      True,
    }


def _sort_jobs(jobs: list[dict], sort: str) -> None:
    if sort == "fit":
        jobs.sort(key=lambda j: j["fit_score"], reverse=True)
    elif sort == "date":
        jobs.sort(key=lambda j: (j.get("is_new", False), j.get("posted_at", "")), reverse=True)
    elif sort == "brazil":
        jobs.sort(key=lambda j: (j.get("is_br", False), j["seniority_score"], j["fit_score"]), reverse=True)
    else:  # seniority (padrão)
        jobs.sort(
            key=lambda j: (j.get("is_new", False), j.get("is_br", False), j["seniority_score"], j["fit_score"]),
            reverse=True,
        )


def _upsert_cache(jobs: list[dict], db: Session) -> None:
    now = datetime.now(timezone.utc)
    for j in jobs:
        existing = db.query(CollectedJob).filter(CollectedJob.id == j["id"]).first()
        if existing:
            existing.last_seen_at = now
            existing.fit_score = j["fit_score"]
            existing.seniority_score = j["seniority_score"]
            existing.seniority_label = j["seniority_label"]
            existing.is_br = j.get("is_br", False)
            existing.is_new = j.get("is_new", False)
        else:
            db.add(CollectedJob(
                id=j["id"],
                title=j["title"],
                company=j["company"],
                location=j["location"],
                url=j["url"],
                description=j["description"],
                source=j["source"],
                posted_at=j["posted_at"],
                is_br=j.get("is_br", False),
                is_new=j.get("is_new", False),
                fit_score=j["fit_score"],
                matched_skills=json.dumps(j["matched_skills"], ensure_ascii=False),
                role_type=j["role_type"],
                seniority_score=j["seniority_score"],
                seniority_label=j["seniority_label"],
                level_signals=json.dumps(j["level_signals"], ensure_ascii=False),
                collected_at=now,
                last_seen_at=now,
            ))
    db.commit()


def _row_to_dict(r: CollectedJob) -> dict:
    try:
        skills = json.loads(r.matched_skills or "[]")
    except Exception:
        skills = []
    try:
        signals = json.loads(r.level_signals or "[]")
    except Exception:
        signals = []
    return {
        "id":              r.id,
        "title":           r.title,
        "company":         r.company,
        "location":        r.location,
        "url":             r.url,
        "description":     r.description,
        "source":          r.source,
        "posted_at":       r.posted_at,
        "is_br":           getattr(r, "is_br", False),
        "is_new":          getattr(r, "is_new", False),
        "fit_score":       r.fit_score,
        "matched_skills":  skills,
        "role_type":       r.role_type,
        "seniority_score": r.seniority_score,
        "seniority_label": r.seniority_label,
        "level_signals":   signals,
    }
