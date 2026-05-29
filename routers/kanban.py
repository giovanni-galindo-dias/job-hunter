from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import KanbanJob
import json

router = APIRouter()

VALID_COLUMNS = {"apply", "ongoing", "interview", "closed"}


@router.get("/")
def list_kanban(db: Session = Depends(get_db)):
    jobs = db.query(KanbanJob).order_by(KanbanJob.added_at.desc()).all()
    return {"jobs": [_serialize(j) for j in jobs]}


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
        score=float(payload.get("score", 0)),
        matched_skills=json.dumps(matched, ensure_ascii=False),
        column="apply",
        posted_at=payload.get("posted_at", ""),
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
    job = db.query(KanbanJob).filter(KanbanJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "not found")
    job.column = col
    db.commit()
    return {"message": "moved", "column": col}


@router.patch("/{job_id}/notes")
def update_notes(job_id: int, payload: dict, db: Session = Depends(get_db)):
    job = db.query(KanbanJob).filter(KanbanJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "not found")
    job.notes = payload.get("notes", "")
    db.commit()
    return {"message": "updated"}


@router.delete("/{job_id}")
def delete_card(job_id: int, db: Session = Depends(get_db)):
    job = db.query(KanbanJob).filter(KanbanJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "not found")
    db.delete(job)
    db.commit()
    return {"message": "deleted"}


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
        "matched_skills": skills,
        "column": j.column,
        "posted_at": j.posted_at,
        "added_at": j.added_at.isoformat() if j.added_at else "",
        "notes": j.notes,
    }
