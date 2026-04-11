from pydantic import BaseModel
from typing import List

class SyllabusRequest(BaseModel):
    topic: str

class SyllabusResponse(BaseModel):
    topic: str
    weeks: List[str]
