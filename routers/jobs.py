from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from database import get_db
from profile import PROFILE
from services.aggregator import aggregate_jobs, load_from_cache, _sort_jobs
from services.matcher import score_fit
from services.seniority_filter import compute_seniority

router = APIRouter()


@router.get("/search")
async def search_jobs(
    sort: str = Query(default="seniority"),         # seniority | fit | date | brazil
    show_ambiguous: bool = Query(default=False),
    brazil_only: bool = Query(default=False),       # filtro geográfico BR
    db: Session = Depends(get_db),
):
    """
    Busca vagas em todas as fontes configuradas em paralelo.
    brazil_only=true → filtra vagas sem localização brasileira.
    """
    result = await aggregate_jobs(
        show_ambiguous=show_ambiguous,
        brazil_only=brazil_only,
        db=db,
    )
    _sort_jobs(result["jobs"], sort)
    return _build_response(result, show_ambiguous)


@router.get("/cache")
def get_cache(
    show_ambiguous: bool = Query(default=False),
    brazil_only: bool = Query(default=False),
    sort: str = Query(default="seniority"),
    db: Session = Depends(get_db),
):
    """Retorna vagas do cache SQLite instantaneamente."""
    cached = load_from_cache(
        db,
        show_ambiguous=show_ambiguous,
        brazil_only=brazil_only,
        sort=sort,
    )
    if not cached:
        return {"jobs": [], "stats": {}, "message": "Cache vazio — clique em 'Nova busca nas APIs'."}
    return _build_response(cached, show_ambiguous)


@router.delete("/cache")
def clear_cache(db: Session = Depends(get_db)):
    from models import CollectedJob
    db.query(CollectedJob).delete()
    db.commit()
    return {"message": "Cache limpo."}


@router.get("/keywords")
def get_keywords():
    return {"keywords": PROFILE["search_keywords"]}


@router.post("/score")
async def score_single(payload: dict):
    title = payload.get("title", "")
    description = payload.get("description", "")
    fit = score_fit(title, description)
    seniority = compute_seniority(title, description)
    return {
        "fit_score":       fit["fit_score"],
        "matched_skills":  fit["matched_skills"],
        "seniority_score": seniority.seniority_score,
        "seniority_label": seniority.seniority_label,
        "level_signals":   seniority.signals,
    }


def _build_response(result: dict, show_ambiguous: bool) -> dict:
    jobs = result["jobs"]
    junior_count    = sum(1 for j in jobs if j["seniority_score"] >= 70)
    ambiguous_count = sum(1 for j in jobs if 40 <= j["seniority_score"] < 70)
    verify_count    = sum(1 for j in jobs if j.get("seniority_label") == "Verificar")
    br_count        = sum(1 for j in jobs if j.get("is_br"))
    new_count       = sum(1 for j in jobs if j.get("is_new"))

    return {
        "jobs": jobs,
        "stats": {
            "total":           len(jobs),
            "junior":          junior_count,
            "ambiguous":       ambiguous_count,
            "verify":          verify_count,
            "brazil":          br_count,
            "new_48h":         new_count,
            "total_collected": result.get("total_collected", len(jobs)),
            "total_deduped":   result.get("total_deduped", len(jobs)),
            "total_filtered":  result.get("total_filtered", len(jobs)),
            "source_stats":    result.get("source_stats", {}),
            "from_cache":      result.get("from_cache", False),
        },
    }
