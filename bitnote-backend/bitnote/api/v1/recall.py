import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Body, Header
from bitnote.core.database import get_db

# from bitnote.core.security import get_current_user
from bitnote.core.ollama_client import generate_structured_response
import time

router = APIRouter(prefix="/recall", tags=["Recall"])


# -----------------------------------------
# Generate Recall Questions
# -----------------------------------------


def extract_json_from_llm(text: str):
    """
    Extracts first valid JSON array/object from LLM output.
    """
    try:
        return json.loads(text)
    except:
        pass

    # Remove markdown fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("[") or part.startswith("{"):
                try:
                    return json.loads(part)
                except:
                    continue

    # Try to find first JSON bracket

    if text.find("[") == -1:
        start = text.find("{")
        end = text.rfind("}")
    else:
        start = text.find("[")
        end = text.rfind("]")

    if start != -1 and end != -1:
        possible_json = text[start : end + 1]
        return json.loads(possible_json)

    raise ValueError("No valid JSON found")


@router.post("/generate/{notebook_id}")
def generate_recall_questions(
    notebook_id: str,
    difficulty: str = Body(...),
    question_count: int = Body(...),
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    # Ownership check
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if difficulty not in ["easy", "normal", "challenging"]:
        raise HTTPException(status_code=400, detail="Invalid difficulty")

    if question_count < 5 or question_count > 15:
        raise HTTPException(status_code=400, detail="Question count must be 5-15")

    session_id = str(uuid.uuid4())

    # Get educational metadata
    edu = db.execute(
        """
        SELECT edu_id, learning_goal, course_topic, syllabus, roadmap, progress
        FROM educational_metadata
        WHERE notebook_id = ?
        """,
        (notebook_id,),
    ).fetchone()

    if not edu:
        raise HTTPException(status_code=400, detail="Not an educational notebook")

    edu_id = edu["edu_id"]

    db.execute(
        """
    INSERT INTO recall_sessions
    (session_id, edu_id, difficulty, question_count)
    VALUES (?, ?, ?, ?)
    """,
        (session_id, edu_id, difficulty, question_count),
    )

    # Fetch full notebook content
    cells = db.execute(
        """
        SELECT user_content
        FROM cells
        WHERE notebook_id = ?
        """,
        (notebook_id,),
    ).fetchall()

    full_content = "\n\n".join([row["user_content"] or "" for row in cells])
    full_content = full_content[:8000]  # safety limit

    # -----------------------------
    # Proper LLM Context Separation
    # -----------------------------

    system_prompt = """
You are a learning scientist designing short recall quizzes.

Rules:
- Questions must be SHORT.
- Prefer MCQ, True/False, or 1-2 word answers.
- Avoid long descriptive questions.
- No explanations.
- Output pure JSON only.
"""

    user_prompt = f"""
Educational Context:

Topic: {edu['course_topic']}
Learning Goal: {edu['learning_goal']}

Notebook Content:
{full_content}

Generate {question_count} recall questions.

Difficulty level: {difficulty}

Rules by difficulty:

Easy:
- Direct fact recall
- Simple MCQs
- Basic true/false

Normal:
- Concept-based MCQs
- Definition recall
- Short answer (1-2 words)

Challenging:
- Application-based MCQs
- Trick true/false
- Very precise short answers

Question types allowed:
- "mcq"
- "true_false"
- "short"

Return JSON format ONLY:

[
  {{
    "question": "...",
    "question_type": "mcq | true_false | short",
    "options": ["A", "B", "C", "D"] OR null,
    "answer": "correct answer"
  }}
]
"""

    response = generate_structured_response(system_prompt, user_prompt)

    try:
        questions = extract_json_from_llm(response)
    except Exception as e:
        print("LLM RAW RESPONSE:\n", response)
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")

    for q in questions:
        db.execute(
            """
            INSERT INTO recall_questions
            (edu_id, question, answer, question_type, options, difficulty, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edu_id,
                q["question"],
                q["answer"],
                q.get("question_type"),
                json.dumps(q.get("options")) if q.get("options") else None,
                difficulty,
                session_id,
            ),
        )

    db.commit()

    return {"message": "Recall questions generated successfully"}


@router.get("/questions/{notebook_id}")
def get_recall_questions(
    notebook_id: str,
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    edu = db.execute(
        "SELECT edu_id FROM educational_metadata WHERE notebook_id = ?",
        (notebook_id,),
    ).fetchone()

    if not edu:
        raise HTTPException(status_code=400, detail="Not educational")

    # ✅ Get latest session from recall_sessions table
    latest_session = db.execute(
        """
        SELECT session_id
        FROM recall_sessions
        WHERE edu_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (edu["edu_id"],),
    ).fetchone()

    if not latest_session:
        return []

    rows = db.execute(
        """
        SELECT id, question, question_type, options
        FROM recall_questions
        WHERE session_id = ?
        """,
        (latest_session["session_id"],),
    ).fetchall()

    return [dict(row) for row in rows]


@router.post("/evaluate")
def evaluate_answer(
    question_id: int = Body(...),
    user_answer: str = Body(...),
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    question = db.execute(
        "SELECT question, answer FROM recall_questions WHERE id = ?",
        (question_id,),
    ).fetchone()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    system_prompt = """
You are a strict academic evaluator.

You must:
- Evaluate student answers objectively
- Avoid hallucination
- Compare strictly against the correct answer
- Score between 0 and 1
"""

    user_prompt = f"""
Question:
{question['question']}

Correct Answer:
{question['answer']}

Student Answer:
{user_answer}

Return ONLY valid JSON:
{{
  "correctness": "correct | partial | incorrect",
  "score": number between 0 and 1,
  "feedback": "short explanation"
}}
"""

    response = generate_structured_response(system_prompt, user_prompt)

    try:
        result = extract_json_from_llm(response)
    except Exception as e:
        print("LLM RAW RESPONSE:\n", response)
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")

    db.execute(
        """
        INSERT INTO recall_attempts (recall_question_id, user_answer, score, feedback)
        VALUES (?, ?, ?, ?)
        """,
        (question_id, user_answer, result["score"], result["feedback"]),
    )

    db.commit()

    return result


@router.get("/stats/{notebook_id}")
def get_stats(
    notebook_id: str,
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    edu = db.execute(
        "SELECT edu_id FROM educational_metadata WHERE notebook_id = ?",
        (notebook_id,),
    ).fetchone()

    if not edu:
        raise HTTPException(status_code=400, detail="Not educational")

    rows = db.execute(
        """
        SELECT score
        FROM recall_attempts ra
        JOIN recall_questions rq ON ra.recall_question_id = rq.id
        WHERE rq.edu_id = ?
        """,
        (edu["edu_id"],),
    ).fetchall()

    if not rows:
        return {"mastery": 0}

    avg = sum(row["score"] for row in rows) / len(rows)

    return {"mastery": round(avg * 100, 2)}


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    # Delete attempts
    db.execute(
        """
        DELETE FROM recall_attempts
        WHERE recall_question_id IN (
            SELECT id FROM recall_questions WHERE session_id = ?
        )
    """,
        (session_id,),
    )

    # Delete questions
    db.execute(
        "DELETE FROM recall_questions WHERE session_id = ?",
        (session_id,),
    )

    # Delete session itself
    db.execute(
        "DELETE FROM recall_sessions WHERE session_id = ?",
        (session_id,),
    )

    db.commit()

    return {"status": "deleted"}


@router.post("/session/complete/{session_id}")
def complete_session(session_id: str, user_id: int, db=Depends(get_db)):

    # Get all scores in this session
    rows = db.execute(
        """
        SELECT ra.score
        FROM recall_attempts ra
        JOIN recall_questions rq ON ra.recall_question_id = rq.id
        WHERE rq.session_id = ?
        """,
        (session_id,),
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=400, detail="No attempts found")

    avg = sum(row["score"] for row in rows) / len(rows)

    db.execute(
        """
        UPDATE recall_sessions
        SET average_score = ?
        WHERE session_id = ?
        """,
        (avg, session_id),
    )

    db.commit()

    return {"session_id": session_id, "average_score": round(avg * 100, 2)}


@router.get("/sessions/{notebook_id}")
def get_sessions(
    notebook_id: str,
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    edu = db.execute(
        "SELECT edu_id FROM educational_metadata WHERE notebook_id = ?",
        (notebook_id,),
    ).fetchone()

    rows = db.execute(
        """
        SELECT session_id, difficulty, question_count, average_score, created_at
        FROM recall_sessions
        WHERE edu_id = ?
        ORDER BY created_at DESC
        """,
        (edu["edu_id"],),
    ).fetchall()

    return [dict(row) for row in rows]


@router.post("/session/evaluate/{session_id}")
def evaluate_session(
    session_id: str,
    answers: dict = Body(...),
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    questions = db.execute(
        """
        SELECT id, question, answer, question_type
        FROM recall_questions
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchall()

    if not questions:
        raise HTTPException(status_code=404, detail="Session not found")

    results = []
    total_score = 0

    for q in questions:
        user_answer = answers.get(str(q["id"]))

        if not user_answer or user_answer.strip() == "":
            user_answer = ""

            result = {
                "score": 0,
                "feedback": "You didn’t answer this. Review this concept and try again.",
            }

            db.execute(
                """
                INSERT INTO recall_attempts
                (recall_question_id, user_answer, score, feedback)
                VALUES (?, ?, ?, ?)
                """,
                (q["id"], user_answer, 0, result["feedback"]),
            )

            results.append(
                {
                    "question_id": q["id"],
                    "score": 0,
                    "feedback": result["feedback"],
                    "correct_answer": q["answer"],
                    "user_answer": "",
                }
            )

            continue

        system_prompt = """
You are an academic evaluator.

Your task is to grade concept understanding — NOT keyword matching.

You MUST classify into EXACTLY one:

- "correct"
- "partial"
- "incorrect"

Evaluation Rules:

1. CORRECT:
   - Student expresses the full meaning of the correct answer.
   - Synonyms count.
   - Reworded explanations count.
   - Conceptual equivalence counts.

2. PARTIAL:
   - Student mentions ONE major idea correctly.
   - But misses other important components.
   - OR gives an answer that is conceptually related but incomplete.

3. INCORRECT:
   - Concept is wrong.
   - Or unrelated.
   - Or contradicts the correct answer.

CRITICAL:
If the correct answer contains multiple ideas
(example: "area and volume")
and the student mentions only ONE of them,
you MUST mark as "partial".

Speak directly to the student using "you".
Keep feedback short (1–2 sentences).
Return ONLY valid JSON.

Format:
{
  "correctness": "correct | partial | incorrect",
  "feedback": "short explanation"
}
"""

        user_prompt = f"""
Question: {q['question']}
Correct Answer: {q['answer']}
Student Answer: {user_answer}
"""

        response = generate_structured_response(system_prompt, user_prompt)
        result = extract_json_from_llm(response)

        score = 0.0

        correctness = result["correctness"]

        if correctness == "correct":
            score = 1.0
        elif correctness == "partial":
            score = 0.6
        else:
            score = 0.0

        db.execute(
            """
            INSERT INTO recall_attempts
            (recall_question_id, user_answer, score, feedback)
            VALUES (?, ?, ?, ?)
            """,
            (q["id"], user_answer, score, result["feedback"]),
        )

        total_score += score

        results.append(
            {
                "question_id": q["id"],
                "score": score,
                "feedback": result["feedback"],
                "correct_answer": q["answer"],
                "user_answer": user_answer,
            }
        )

    average = total_score / len(questions)

    db.execute(
        """
        UPDATE recall_sessions
        SET average_score = ?
        WHERE session_id = ?
        """,
        (average * 100, session_id),
    )

    db.commit()

    return {"results": results, "average_score": round(average * 100, 2)}


@router.get("/questions/session/{session_id}")
def get_session_questions(
    session_id: str,
    user_id: int = Header(..., alias="x-user-id"),
    db=Depends(get_db),
):

    rows = db.execute(
        """
        SELECT 
            rq.id,
            rq.question,
            rq.question_type,
            rq.options,
            rq.answer AS correct_answer,
            ra.user_answer,
            ra.score,
            ra.feedback
        FROM recall_questions rq
        LEFT JOIN recall_attempts ra 
            ON rq.id = ra.recall_question_id
        WHERE rq.session_id = ?
        """,
        (session_id,),
    ).fetchall()

    return [dict(row) for row in rows]
