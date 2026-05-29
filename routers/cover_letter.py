from fastapi import APIRouter
from services.cover_letter import generate

router = APIRouter()


@router.post("/generate")
def generate_cover_letter(payload: dict):
    title = payload.get("title", "")
    company = payload.get("company", "")
    description = payload.get("description", "")
    if not description:
        return {"error": "description required"}
    text = generate(title, company, description)
    return {"letter": text}
