from pydantic import BaseModel
from typing import Optional, List


class LearningPlanRequest(BaseModel):
    topic: str
    level: str
    time_per_day: int
    course_topic: Optional[str] = None


class LearningDay(BaseModel):
    day: int
    task: str


class LearningWeek(BaseModel):
    week: int
    focus: str
    days: List[LearningDay]


class LearningPlanResponse(BaseModel):
    topic: str
    level: str
    learning_goal: str
    syllabus: List[str]
    roadmap: List[LearningWeek]
    checklist: List[str]
