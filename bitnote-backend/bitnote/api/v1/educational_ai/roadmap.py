from fastapi import APIRouter
from bitnote.schemas.roadmap import RoadmapRequest, RoadmapStep, RoadmapResponse
from bitnote.services.educational_ai.roadmap_service import generate_roadmap

router = APIRouter()

@router.post("/roadmap", response_model=RoadmapResponse)
def create_roadmap(request: RoadmapRequest):
    """
    Generates a roadmap for a given topic.
    """
    return generate_roadmap(request.topic)