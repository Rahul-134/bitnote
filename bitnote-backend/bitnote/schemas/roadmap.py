from pydantic import BaseModel

class RoadmapRequest(BaseModel):
    topic: str

class RoadmapStep(BaseModel):
    week: int
    title: str
    goal: list[str]

class RoadmapResponse(BaseModel):
    topic: str
    estimated_duration_weeks: int
    roadmap: list[RoadmapStep]