import json
import re


def extract_json(text: str) -> dict:
    """
    Extracts first JSON object from model output
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")

    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON structure")
