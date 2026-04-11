from fastapi import APIRouter
from bitnote.schemas.checklist_schema import (ChecklistRequest, ChecklistResponse)
from bitnote.services.educational_ai.checklist_service import generate_checklist

router = APIRouter()


@router.post("/checklist", response_model=ChecklistResponse, summary="Generate learning checklist / timeline")
def create_learning_checklist(request: ChecklistRequest):
    return generate_checklist(
        topic = request.topic,
        roadmap = request.roadmap
    )