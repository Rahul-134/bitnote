from fastapi import APIRouter
from bitnote.schemas.syllabus import SyllabusRequest, SyllabusResponse
from bitnote.services.educational_ai.syllabus_service import generate_syllabus

router = APIRouter()

@router.post("/syllabus", response_model=SyllabusResponse)
def create_syllabus(request: SyllabusRequest):
    """
    Generates a syllabus for a given topic.
    """
    return generate_syllabus(request.topic)
