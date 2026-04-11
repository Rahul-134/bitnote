import ollama

MODEL_NAME = "gemma3"

SYSTEM_PROMPT = """
You are an AI assistant for a note-taking app.

Generate a concise notebook description.

Rules:
- 15 to 20 words
- Plain text only
- No emojis
- No quotes
- No markdown
- Educational tone
"""

def generate_notebook_description(title: str) -> str:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Notebook Title: {title}",
            },
        ],
    )

    text = response["message"]["content"].strip()

    if len(text.split()) < 5:
        return f"Educational Notebook for structured learning and revision on {title}"
    
    return text