import ollama
from bitnote.schemas.learning_plan import LearningPlanRequest, LearningPlanResponse
from bitnote.utils.json_utils import extract_json

MODEL_NAME = "gemma3"

SYSTEM_PROMPT = """

You are an Educational AI system for a note-taking and learning application called BitNote.

Your task is to generate a COMPLETE, STRUCTURED learning plan.

You MUST follow ALL rules below EXACTLY.

━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━

1. You MUST return ONLY valid JSON.
2. The output MUST start with { and end with }.
3. Do NOT include explanations, comments, markdown, or extra text.
4. Do NOT omit any required fields.
5. Do NOT add any extra fields.
6. Field names, nesting, and data types MUST match the schema EXACTLY.
7. If you are unsure, still produce the closest valid structured answer — NEVER break schema.

If you violate ANY rule, the response will be rejected.

━━━━━━━━━━━━━━━━━━━━━━
INPUT YOU WILL RECEIVE
━━━━━━━━━━━━━━━━━━━━━━

You will receive:
- topic (string)
- level (string)
- daily time available in minutes (integer)

Use these to adapt depth and pacing.

━━━━━━━━━━━━━━━━━━━━━━
REQUIRED JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━

You MUST return JSON in EXACTLY this structure:

{
  "topic": "<string>",
  "level": "<string>",
  "learning_goal": "<clear single-sentence goal>",

  "syllabus": [
    "<high-level topic 1>",
    "<high-level topic 2>",
    "<high-level topic 3>"
  ],

  "roadmap": [
    {
      "week": <number>,
      "focus": "<main focus of the week>",
      "days": [
        {
          "day": <number>,
          "task": "<specific actionable learning task>"
        }
      ]
    }
  ],

  "checklist": [
    "<actionable completion item 1>",
    "<actionable completion item 2>"
  ]
}

━━━━━━━━━━━━━━━━━━━━━━
CONTENT RULES
━━━━━━━━━━━━━━━━━━━━━━

• syllabus:
  - High-level topics only
  - Ordered logically from beginner → advanced

• roadmap:
  - Weeks MUST start from 1 and increment sequentially
  - Each week MUST contain at least 3 days
  - Tasks must be specific and actionable
  - Roadmap length should reasonably match the topic and level

• checklist:
  - Must be derived from the roadmap
  - Should represent meaningful completion milestones
  - Final item should reflect a capstone or applied outcome

━━━━━━━━━━━━━━━━━━━━━━
QUALITY BAR
━━━━━━━━━━━━━━━━━━━━━━

- Be practical, not academic
- Avoid vague phrases like “learn about”
- Prefer tasks that could realistically be completed in the given daily time
- The output should feel like a real learning plan a human would follow

Remember:
Return ONLY the JSON object.
Nothing else.


"""


def generate_learning_plan(payload: LearningPlanRequest) -> LearningPlanResponse:
    """
    Generates a complete structured learning plan.
    This function is STRICT by design.
    """

    focus_line = (
        f"Focus area: {payload.course_topic}\n"
        if payload.course_topic else ""
    )

    user_prompt = f"""
Primary subject: {payload.topic}
{focus_line}Level: {payload.level}
Daily time available: {payload.time_per_day} minutes
"""

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_output = response["message"]["content"]

    # Extract JSON (or fail)
    parsed_json = extract_json(raw_output)

    # Validate against schema (or fail)
    learning_plan = LearningPlanResponse(**parsed_json)

    return learning_plan
