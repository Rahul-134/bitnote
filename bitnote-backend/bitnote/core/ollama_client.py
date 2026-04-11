import ollama

MODEL_NAME = "gemma3"  # change if needed


def generate_structured_response(system_prompt: str, user_prompt: str) -> str:
    """
    Calls Ollama and returns raw text response
    """
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response["message"]["content"]


def generate_chat_response(messages: list) -> str:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
    )
    return response["message"]["content"]
