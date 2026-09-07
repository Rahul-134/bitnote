from typing import List, Literal, Optional

from pydantic import BaseModel

# Literal (not plain str) so structured-output constraining actually enforces
# these exact values on both providers, instead of letting a model invent a
# differently-cased or -spelled variant (e.g. "trueFalse", "Incorrect") that
# the app's own string comparisons would silently fail to match.

QuestionType = Literal["mcq", "true_false", "short"]
Correctness = Literal["correct", "partial", "incorrect"]


class RecallQuestionItem(BaseModel):
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    answer: str


class AnswerEvaluation(BaseModel):
    correctness: Correctness
    score: float
    feedback: str


class SessionAnswerEvaluation(BaseModel):
    correctness: Correctness
    feedback: str
