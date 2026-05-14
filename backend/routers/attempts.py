from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import storage

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SubmitAttemptRequest(BaseModel):
    answers: dict[str, str]


class AttemptResult(BaseModel):
    attempt_id: str
    score: int
    total: int
    percentage: float
    wrong_indices: list[int]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/attempts/{quiz_id}", response_model=AttemptResult)
def submit_attempt(quiz_id: str, request: SubmitAttemptRequest):
    # Step 1 — load quiz
    quiz = storage.read_json(storage.quiz_path(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail=f"Quiz '{quiz_id}' not found")

    # Step 2 — validate submitted answer values
    valid_letters = {"A", "B", "C", "D"}
    for key, value in request.answers.items():
        if value not in valid_letters:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid answer value: '{value}'. Must be A, B, C, or D",
            )

    # Step 3 — score the attempt
    score = 0
    wrong_indices: list[int] = []

    for question in quiz["questions"]:
        correct = question["correct_answer"]
        submitted = request.answers.get(str(question["index"]))
        if submitted == correct:
            score += 1
        else:
            wrong_indices.append(question["index"])

    total = len(quiz["questions"])
    percentage = round((score / total) * 100, 1) if total > 0 else 0.0

    # Step 4 — build attempt object
    now = datetime.utcnow()
    attempt_id = f"atmp_{int(now.timestamp())}"
    attempted_at = now.isoformat() + "Z"

    attempt_obj = {
        "attempt_id": attempt_id,
        "attempted_at": attempted_at,
        "score": score,
        "total": total,
        "percentage": percentage,
        "answers": dict(request.answers),
        "wrong_indices": wrong_indices,
    }

    # Step 5 — write to attempts file
    attempts_data = storage.read_json(storage.attempts_path(quiz_id))
    if not attempts_data:
        attempts_data = {"quiz_id": quiz_id, "attempts": []}
    attempts_data["attempts"].append(attempt_obj)
    storage.write_json(storage.attempts_path(quiz_id), attempts_data)

    # Step 6 — write wrong answers to wrong.json (AFTER attempt write succeeds)
    if wrong_indices:
        wrong_entries = []
        for wrong_index in wrong_indices:
            question = quiz["questions"][wrong_index]
            wrong_entries.append(
                {
                    "quiz_id": quiz["id"],
                    "quiz_title": quiz["title"],
                    "question_index": question["index"],
                    "question_text": question["text"],
                    "code": question["code"],
                    "code_language": question["code_language"],
                    "options": question["options"],
                    "your_answer": request.answers.get(str(wrong_index)),
                    "correct_answer": question["correct_answer"],
                    "attempt_id": attempt_id,
                    "attempted_at": attempted_at,
                }
            )
        wrong_list = storage.read_json(storage.wrong_path())
        wrong_list.extend(wrong_entries)
        storage.write_json(storage.wrong_path(), wrong_list)

    # Step 7 — return result
    return AttemptResult(
        attempt_id=attempt_id,
        score=score,
        total=total,
        percentage=percentage,
        wrong_indices=wrong_indices,
    )


@router.get("/attempts/{quiz_id}")
def get_attempts(quiz_id: str):
    data = storage.read_json(storage.attempts_path(quiz_id))
    if not data:
        return {"quiz_id": quiz_id, "attempts": []}
    attempts = sorted(data.get("attempts", []), key=lambda a: a["attempted_at"], reverse=True)
    return {"quiz_id": quiz_id, "attempts": attempts}


@router.get("/attempts/{quiz_id}/{attempt_id}")
def get_attempt(quiz_id: str, attempt_id: str):
    data = storage.read_json(storage.attempts_path(quiz_id))
    if not data:
        raise HTTPException(status_code=404, detail=f"No attempts found for quiz '{quiz_id}'")

    for attempt in data.get("attempts", []):
        if attempt["attempt_id"] == attempt_id:
            return attempt

    raise HTTPException(status_code=404, detail=f"Attempt '{attempt_id}' not found")
