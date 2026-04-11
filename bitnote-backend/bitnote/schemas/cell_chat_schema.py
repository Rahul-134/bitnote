from pydantic import BaseModel
from typing import List


class ChatMessage(BaseModel):
    role: str
    content: str


class CellChatRequest(BaseModel):
    notebook_id: str
    cell_id: str
    cell_content: str
    conversation: List[ChatMessage]
    user_message: str
