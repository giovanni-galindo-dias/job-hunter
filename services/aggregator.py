"""
Orquestrador central de vagas.

Pipeline:
  1. Executa todos os coletores em PARALELO (asyncio.gather).
  2. Achata os resultados em uma lista única.
  3. Deduplica por (título normalizado, empresa normalizada).
  4. Aplica filtragem de senioridade (4 camadas).
  5. Calcula fit_score e seniority_score.
  6. Persiste no cache SQLite (upsert por id).
  7. Retorna vagas + estatísticas por fonte.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from collectors.registry import COLLECTORS
from collectors.base import RawJob, CollectorResult
from models import CollectedJob
from services.matcher import score_fit
from services.seniority_filter import compute_seniority, DEFAULT_MIN_SCORE, AMBIGUOUS_MIN_SCORE


# ── Deduplicação ──────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {
    "Google Jobs": 1,
    "Adzuna":      2,
    "JSearch":     3,
    "Remotive":    4,
    "RemoteOK":    5,
    "Arbeitnow":   6,
    "The Muse":    7,
}


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _dedup(jobs: list[RawJob]) -> list[RawJob]:
    """
    Mantém uma vaga por (título_normalizado, empresa_normalizada).
    Prefere a fonte de maior prioridade quando há duplicata.
    """
    seen: dict[str, RawJob] = {}
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
    db: Session | None = None,
) -> dict:
    """
    Coleta vagas de todas as fontes em paralelo, filtra e retorna.

    Returns:
        jobs:             list[dict] — vagas prontas para exibição
        source_stats:     dict — por fonte: {collected, error}
        total_collected:  int — total antes do dedup
        total_deduped:    int — total após dedup
        total_filtered:   int — total após filtro de senioridade
    """
    # Executa todos os coletores em paralelo
    tasks = [c.collect([]) for c in COLLECTORS]
    results: list[CollectorResult] = await asyncio.gather(*tasks)

    # Agrega e coleta estatísticas por fonte
    all_raw: list[RawJob] = []
    source_stats: dict[str, dict] = {}
    for res in results:
        source_stats[res.name] = {
            "collected": len(res.jobs),
            "error": res.error,
        }
        all_raw.extend(res.jobs)

    total_collected = len(all_raw)

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
        processed.append({
            "id":               raw.job_id,
            "title":            raw.title,
            "company":          raw.company,
            "location":         raw.location,
            "url":              raw.url,
            "description":      raw.description[:2000],
            "source":           raw.source,
            "posted_at":        raw.posted_at,
            "fit_score":        fit["fit_score"],
            "matched_skills":   fit["matched_skills"],
            "role_type":        fit["role_type"],
            "seniority_score":  seniority.seniority_score,
            "seniority_label":  seniority.seniority_label,
            "level_signals":    seniority.signals,
        })

    total_filtered = len(processed)

    # Ordenação: seniority DESC → fit DESC
    processed.sort(key=lambda j: (j["seniority_score"], j["fit_score"]), reverse=True)

    # Persiste no cache SQLite
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
    sort: str = "seniority",
) -> dict | None:
    """
    Retorna vagas do cache SQLite se houver resultados.
    Retorna None se o cache estiver vazio.
    """
    min_score = AMBIGUOUS_MIN_SCORE if show_ambiguous else DEFAULT_MIN_SCORE
    rows = (
        db.query(CollectedJob)
        .filter(CollectedJob.seniority_score >= min_score)
        .all()
    )
    if not rows:
        return None

    jobs = [_row_to_dict(r) for r in rows]
    _sort_jobs(jobs, sort)

    source_counts: dict[str, int] = {}
    for j in jobs:
        source_counts[j["source"]] = source_counts.get(j["source"], 0) + 1

    source_stats = {src: {"collected": cnt, "error": None} for src, cnt in source_counts.items()}

    return {
        "jobs":            jobs,
        "source_stats":    source_stats,
        "total_collected": len(jobs),
        "total_deduped":   len(jobs),
        "total_filtered":  len(jobs),
        "from_cache":      True,
    }


def _sort_jobs(jobs: list[dict], sort: str) -> None:
    if sort == "fit":
        jobs.sort(key=lambda j: j["fit_score"], reverse=True)
    elif sort == "date":
        jobs.sort(key=lambda j: j.get("posted_at", ""), reverse=True)
    else:
        jobs.sort(key=lambda j: (j["seniority_score"], j["fit_score"]), reverse=True)


def _upsert_cache(jobs: list[dict], db: Session) -> None:
    now = datetime.now(timezone.utc)
    for j in jobs:
        existing = db.query(CollectedJob).filter(CollectedJob.id == j["id"]).first()
        if existing:
            existing.last_seen_at = now
            existing.fit_score = j["fit_score"]
            existing.seniority_score = j["seniority_score"]
            existing.seniority_label = j["seniority_label"]
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
        "fit_score":       r.fit_score,
        "matched_skills":  skills,
        "role_type":       r.role_type,
        "seniority_score": r.seniority_score,
        "seniority_label": r.seniority_label,
        "level_signals":   signals,
    }
