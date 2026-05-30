"""
Orquestrador central de vagas — com logging completo de funil.

Pipeline e contagens por estágio:
  [coletor] raw=N  (ou error=...)
  flatten=N
  pos_dedup=N
  pos_geo_filter=N
  pos_seniority=N
  final=N
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import traceback
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from collectors.registry import COLLECTORS, BR_NATIVE_SOURCES
from collectors.base import RawJob, CollectorResult
from models import CollectedJob
from services.matcher import score_fit
from services.seniority_filter import compute_seniority, DEFAULT_MIN_SCORE, AMBIGUOUS_MIN_SCORE

log = logging.getLogger("job_hunter.aggregator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ── Geo-filter ────────────────────────────────────────────────────────────────

_BR_LOCATION_KW = {
    "brasil", "brazil",
    "são paulo", "sp", "sao paulo",
    "rio de janeiro", "rj",
    "minas gerais", "mg", "belo horizonte",
    "porto alegre", "rs", "curitiba", "pr",
    "salvador", "ba", "recife", "pe", "fortaleza", "ce",
    "brasília", "brasilia", "df", "distrito federal",
    "guaratinguetá", "guaratingueta", "campinas",
    "remoto", "remoto (brasil)", "remoto brasil",
    "remote", "híbrido", "hibrido", "hybrid",
}


def _is_brazil_job(source: str, location: str) -> bool:
    """
    True se:
     - fonte é nativamente brasileira (Gupy, Adzuna)
     - OU localização contém keyword de cidade/estado BR
    Falha-aberta: location vazia de fonte nativa ainda é BR.
    """
    if source in BR_NATIVE_SOURCES:
        return True
    if not location:
        return False
    loc = location.lower()
    return any(kw in loc for kw in _BR_LOCATION_KW)


# ── 48h detector ─────────────────────────────────────────────────────────────

def _is_recent(posted_at: str) -> bool:
    if not posted_at:
        return False
    try:
        posted = datetime.strptime(posted_at[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - posted) <= timedelta(hours=48)
    except Exception:
        return False


# ── Deduplicação ──────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {
    "Gupy":        1,
    "Google Jobs": 2,
    "Adzuna":      3,
    "JSearch":     4,
    "Remotive":    5,
    "RemoteOK":    6,
    "Arbeitnow":   7,
    "The Muse":    8,
}


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _dedup(jobs: list[RawJob]) -> list[RawJob]:
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


# ── Coleta paralela com logging ───────────────────────────────────────────────

async def _collect_all() -> tuple[list[RawJob], dict[str, dict]]:
    """
    Executa todos os coletores em paralelo.
    Erros são capturados POR COLETOR (nunca derrubam a busca inteira)
    e logados com traceback.
    """
    tasks = [c.collect([]) for c in COLLECTORS]
    results: list[CollectorResult] = await asyncio.gather(*tasks)

    all_raw: list[RawJob] = []
    source_stats: dict[str, dict] = {}

    for res in results:
        stat: dict = {
            "collected": len(res.jobs),
            "error":     res.error,
            "is_br":     res.name in BR_NATIVE_SOURCES,
        }
        source_stats[res.name] = stat

        if res.error:
            log.warning("[%s] FALHOU: %s", res.name, res.error)
        else:
            log.info("[%s] raw=%d", res.name, len(res.jobs))

        all_raw.extend(res.jobs)

    log.info("flatten=%d", len(all_raw))
    return all_raw, source_stats


# ── Pipeline principal ────────────────────────────────────────────────────────

async def aggregate_jobs(
    show_ambiguous: bool = False,
    brazil_only: bool = False,
    db: Session | None = None,
) -> dict:
    all_raw, source_stats = await _collect_all()
    total_collected = len(all_raw)

    # Geo-filter (opcional — quando brazil_only=False não descarta nada)
    if brazil_only:
        before_geo = len(all_raw)
        all_raw = [j for j in all_raw if _is_brazil_job(j.source, j.location)]
        log.info("pos_geo_filter=%d (descartados=%d)", len(all_raw), before_geo - len(all_raw))
    else:
        log.info("geo_filter=skip (brazil_only=False)")

    # Deduplicação
    unique = _dedup(all_raw)
    total_deduped = len(unique)
    log.info("pos_dedup=%d", total_deduped)

    # Score + filtro de senioridade
    min_score = AMBIGUOUS_MIN_SCORE if show_ambiguous else DEFAULT_MIN_SCORE
    discarded_seniority = 0
    processed: list[dict] = []

    for raw in unique:
        seniority = compute_seniority(raw.title, raw.description)
        if seniority.seniority_score < min_score:
            discarded_seniority += 1
            continue
        fit = score_fit(raw.title, raw.description)
        is_br = _is_brazil_job(raw.source, raw.location)
        is_new = _is_recent(raw.posted_at)

        processed.append({
            "id":              raw.job_id,
            "title":           raw.title,
            "company":         raw.company,
            "location":        raw.location,
            "url":             raw.url,
            "description":     raw.description[:2000],
            "source":          raw.source,
            "posted_at":       raw.posted_at,
            "is_br":           is_br,
            "is_new":          is_new,
            "fit_score":       fit["fit_score"],
            "matched_skills":  fit["matched_skills"],
            "role_type":       fit["role_type"],
            "seniority_score": seniority.seniority_score,
            "seniority_label": seniority.seniority_label,
            "level_signals":   seniority.signals,
        })

    total_filtered = len(processed)
    log.info(
        "pos_seniority=%d (descartados=%d, min_score=%d)",
        total_filtered, discarded_seniority, min_score,
    )
    log.info("final=%d", total_filtered)

    # Ordenação: novas BR primeiro → seniority DESC → fit DESC
    processed.sort(
        key=lambda j: (
            j["is_new"],
            j["is_br"],
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
        # diagnóstico extra
        "discarded_seniority": discarded_seniority,
    }


# ── Diagnóstico completo ──────────────────────────────────────────────────────

async def run_diagnostics() -> dict:
    """
    Executa coleta completa e devolve contagens por estágio + por coletor.
    Exposto em GET /api/jobs/debug — não persiste no cache.
    """
    log.info("=== DIAGNÓSTICO INICIADO ===")
    all_raw, source_stats = await _collect_all()

    # Dedup sem geo-filter
    unique_all = _dedup(all_raw)

    # Geo-filter
    br_only = [j for j in unique_all if _is_brazil_job(j.source, j.location)]

    # Seniority com threshold padrão
    passed_default: list[dict] = []
    passed_ambiguous: list[dict] = []
    discarded: list[dict] = []

    for raw in unique_all:
        s = compute_seniority(raw.title, raw.description)
        entry = {
            "title":           raw.title,
            "company":         raw.company,
            "source":          raw.source,
            "seniority_score": s.seniority_score,
            "seniority_label": s.seniority_label,
            "signals":         s.signals,
            "is_br":           _is_brazil_job(raw.source, raw.location),
        }
        if s.seniority_score >= DEFAULT_MIN_SCORE:
            passed_default.append(entry)
        elif s.seniority_score >= AMBIGUOUS_MIN_SCORE:
            passed_ambiguous.append(entry)
        else:
            discarded.append(entry)

    log.info("=== DIAGNÓSTICO CONCLUÍDO ===")
    return {
        "pipeline": {
            "flatten":          len(all_raw),
            "pos_dedup":        len(unique_all),
            "pos_geo_br_only":  len(br_only),
            "pos_seniority_default":   len(passed_default),
            "pos_seniority_ambiguous": len(passed_default) + len(passed_ambiguous),
            "discarded_seniority":     len(discarded),
            "DEFAULT_MIN_SCORE":       DEFAULT_MIN_SCORE,
            "AMBIGUOUS_MIN_SCORE":     AMBIGUOUS_MIN_SCORE,
        },
        "sources": source_stats,
        "samples_passed": passed_default[:5],
        "samples_discarded": discarded[:5],
        "samples_ambiguous": passed_ambiguous[:5],
    }


# ── Cache helpers ─────────────────────────────────────────────────────────────

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
            source_counts[src] = {
                "collected": 0,
                "error": None,
                "is_br": j.get("is_br", False),
            }
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
        jobs.sort(
            key=lambda j: (j.get("is_new", False), j.get("posted_at", "")),
            reverse=True,
        )
    elif sort == "brazil":
        jobs.sort(
            key=lambda j: (j.get("is_br", False), j["seniority_score"], j["fit_score"]),
            reverse=True,
        )
    else:
        jobs.sort(
            key=lambda j: (
                j.get("is_new", False),
                j.get("is_br", False),
                j["seniority_score"],
                j["fit_score"],
            ),
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
