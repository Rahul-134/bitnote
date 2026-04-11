from pydantic import BaseModel
from typing import List

class ChecklistRequest(BaseModel):
    topic: str
    roadmap: List[str]

class ChecklistItem(BaseModel):
    title: str
    tasks: List[str]

class ChecklistResponse(BaseModel):
    topic: str
    checklist: List[ChecklistItem]