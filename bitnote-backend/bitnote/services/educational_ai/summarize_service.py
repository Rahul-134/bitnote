import requests
from requests.exceptions import ReadTimeout


def generate_summary_with_ollama(content: str) -> str:
    prompt = f"""
Summarize the following notes clearly and concisely.

Rules:
- Use short bullet points.
- Preserve mathematical formulas.
- Write all mathematical expressions in LaTeX format.
- Use $...$ for inline math.
- Use $$...$$ for important displayed equations.
- Do not add extra information.
- Use natural academic language.
- Do not mention instructions.
- Do not refer to this prompt.
- Do not add unrelated explanations.
- Keep the explanation natural and easy to revise from.

NOTES:
{content}
"""

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "gemma3", "prompt": prompt, "stream": False},
            timeout=180, 
        )

        if res.status_code != 200:
            raise Exception("Ollama failed")

        return res.json()["response"].strip()

    except ReadTimeout:
        raise Exception("AI generation timed out. Try shorter content.")
