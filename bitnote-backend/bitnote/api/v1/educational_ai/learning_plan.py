from fastapi import APIRouter, HTTPException
from bitnote.schemas.learning_plan import LearningPlanRequest, LearningPlanResponse
from bitnote.services.educational_ai.learning_plan_service import generate_learning_plan

router = APIRouter()


@router.post("/learning_plan", response_model=LearningPlanResponse)
async def learning_plan(payload: LearningPlanRequest):
    try:
        return generate_learning_plan(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
