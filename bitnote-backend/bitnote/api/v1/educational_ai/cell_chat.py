from fastapi import APIRouter
from bitnote.schemas.cell_chat_schema import CellChatRequest
from bitnote.services.educational_ai.cell_chat_service import generate_cell_chat_response

router = APIRouter()

@router.post("/cell-chat")
async def cell_chat(request: CellChatRequest):
    reply = generate_cell_chat_response(request)
    return {"reply": reply}
