from bitnote.core.llm_client import generate_text

SYSTEM_PROMPT = """
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
"""


def generate_summary_with_ollama(content: str) -> str:
    try:
        return generate_text(SYSTEM_PROMPT, content).strip()
    except Exception as e:
        raise Exception(f"AI generation failed. Try shorter content. ({e})")
