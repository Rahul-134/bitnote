from bitnote.schemas.cell_chat_schema import CellChatRequest
from bitnote.core.ollama_client import generate_chat_response


def generate_cell_chat_response(request: CellChatRequest) -> str:

    messages = []

    system_prompt = f"""
You are BitBuddy.

You are a study companion and tutor.

STRICT RULES:
- Only answer using the provided cell content.
- If question is unrelated, respond:
  "This question is not related to this cell's content."
- Do NOT hallucinate.
- Occasionally:
  - Ask a recall question.
  - Provide constructive feedback.
  - Challenge understanding.

CELL CONTENT:
{request.cell_content}
"""

    messages.append({"role": "system", "content": system_prompt})

    for msg in request.conversation:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.user_message})

    return generate_chat_response(messages)
