from fastapi import APIRouter

from app.schemas import SymptomSearchRequest, SymptomSearchResponse
from app.services.symptom_match import match_symptom

router = APIRouter(tags=["symptom-search"])


@router.post("/symptom-search", response_model=SymptomSearchResponse)
async def symptom_search(payload: SymptomSearchRequest):
    result = await match_symptom(payload.text)
    return SymptomSearchResponse(
        emergency=result.emergency,
        specialty=result.specialty,
        source=result.source,
        message=result.message,
        matched_phrase=result.matched_phrase,
    )
