from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from models import KanbanJob
import json

router = APIRouter()

VALID_COLUMNS = {"apply", "ongoing", "interview", "closed"}


@router.get("/")
def list_kanban(db: Session = Depends(get_db)):
    jobs = db.query(KanbanJob).order_by(KanbanJob.added_at.desc()).all()
    return {"jobs": [_serialize(j) for j in jobs]}


@router.get("/stats")
def kanban_stats(db: Session = Depends(get_db)):
    """
    Estatísticas de conversão por fonte — recomendação do conselho.
    Mostra qual canal gerou mais entrevistas.
    """
    jobs = db.query(KanbanJob).all()
    total = len(jobs)
    interviews = sum(1 for j in jobs if j.interview_scheduled)
    offers = sum(1 for j in jobs if j.offer_received)

    # Taxa de conversão por fonte
    by_source: dict[str, dict] = {}
    for j in jobs:
        src = j.source or "Desconhecido"
        if src not in by_source:
            by_source[src] = {"total": 0, "interviews": 0, "offers": 0}
        by_source[src]["total"] += 1
        if j.interview_scheduled:
            by_source[src]["interviews"] += 1
        if j.offer_received:
            by_source[src]["offers"] += 1

    # Ordenar por número de entrevistas
    ranked = sorted(by_source.items(), key=lambda x: x[1]["interviews"], reverse=True)

    return {
        "total": total,
        "interviews": interviews,
        "offers": offers,
        "conversion_rate": round(interviews / max(total, 1) * 100, 1),
        "by_source": dict(ranked),
    }


@router.post("/add")
def add_to_kanban(payload: dict, db: Session = Depends(get_db)):
    ext_id = payload.get("external_id") or payload.get("id", "")
    if not ext_id:
        raise HTTPException(400, "external_id required")

    existing = db.query(KanbanJob).filter(KanbanJob.external_id == ext_id).first()
    if existing:
        return {"message": "already_exists", "job": _serialize(existing)}

    matched = payload.get("matched_skills", [])
    job = KanbanJob(
        external_id=ext_id,
        title=payload.get("title", ""),
        company=payload.get("company", ""),
        location=payload.get("location", ""),
        url=payload.get("url", ""),
        description=payload.get("description", ""),
        source=payload.get("source", "manual"),
        score=float(payload.get("fit_score", payload.get("score", 0))),
        seniority_score=int(payload.get("seniority_score", 0)),
        seniority_label=payload.get("seniority_label", ""),
        matched_skills=json.dumps(matched, ensure_ascii=False),
        column="apply",
        posted_at=payload.get("posted_at", ""),
        is_br=payload.get("is_br", False),
        applied_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"message": "added", "job": _serialize(job)}


@router.patch("/{job_id}/move")
def move_card(job_id: int, payload: dict, db: Session = Depends(get_db)):
    col = payload.get("column", "")
    if col not in VALID_COLUMNS:
        raise HTTPException(400, f"column must be one of {VALID_COLUMNS}")
    job = _get_or_404(db, job_id)
    job.column = col
    # Se moveu para "interview", marca automaticamente interview_scheduled
    if col == "interview":
        job.interview_scheduled = True
    db.commit()
    return {"message": "moved", "column": col}


@router.patch("/{job_id}/notes")
def update_notes(job_id: int, payload: dict, db: Session = Depends(get_db)):
    job = _get_or_404(db, job_id)
    job.notes = payload.get("notes", "")
    db.commit()
    return {"message": "updated"}


@router.patch("/{job_id}/interview")
def toggle_interview(job_id: int, payload: dict, db: Session = Depends(get_db)):
    """Marca/desmarca entrevista — para rastreamento de conversão por fonte."""
    job = _get_or_404(db, job_id)
    job.interview_scheduled = payload.get("interview_scheduled", not job.interview_scheduled)
    if payload.get("offer_received") is not None:
        job.offer_received = payload["offer_received"]
    db.commit()
    return {"message": "updated", "interview_scheduled": job.interview_scheduled}


@router.delete("/{job_id}")
def delete_card(job_id: int, db: Session = Depends(get_db)):
    job = _get_or_404(db, job_id)
    db.delete(job)
    db.commit()
    return {"message": "deleted"}


def _get_or_404(db: Session, job_id: int) -> KanbanJob:
    job = db.query(KanbanJob).filter(KanbanJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "not found")
    return job


def _serialize(j: KanbanJob) -> dict:
    try:
        skills = json.loads(j.matched_skills or "[]")
    except Exception:
        skills = []
    return {
        "id": j.id,
        "external_id": j.external_id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "url": j.url,
        "source": j.source,
        "score": j.score,
        "fit_score": j.score,
        "seniority_score": j.seniority_score or 0,
        "seniority_label": j.seniority_label or "",
        "matched_skills": skills,
        "column": j.column,
        "posted_at": j.posted_at,
        "added_at": j.added_at.isoformat() if j.added_at else "",
        "applied_at": j.applied_at.isoformat() if j.applied_at else "",
        "notes": j.notes,
        "interview_scheduled": j.interview_scheduled or False,
        "offer_received": j.offer_received or False,
        "is_br": j.is_br or False,
    }
