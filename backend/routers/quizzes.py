import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from services import md_parser, storage

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QuizUploadResponse(BaseModel):
    quiz_id: str
    title: str
    filename: str
    question_count: int
    uploaded_at: str


class QuizSummary(BaseModel):
    id: str
    title: str
    filename: str
    uploaded_at: str
    question_count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/quizzes/upload", response_model=QuizUploadResponse, status_code=200)
async def upload_quiz(file: UploadFile):
    # Step 1 — validate file type
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are accepted")

    # Step 2 — read and decode
    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    # Step 3 — parse
    try:
        parsed = md_parser.parse_quiz(raw_text, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Step 4 — generate unique quiz ID (8 hex chars)
    quiz_id = uuid.uuid4().hex[:8]
    while storage.quiz_path(quiz_id).exists():
        quiz_id = uuid.uuid4().hex[:8]

    # Step 5 — build quiz dict
    uploaded_at = datetime.utcnow().isoformat() + "Z"
    quiz_dict = {
        "id": quiz_id,
        "title": parsed["title"],
        "filename": file.filename,
        "uploaded_at": uploaded_at,
        "question_count": parsed["question_count"],
        "questions": parsed["questions"],
    }

    # Step 6 — write to disk
    storage.write_json(storage.quiz_path(quiz_id), quiz_dict)

    # Step 7 — return summary (no questions array)
    return QuizUploadResponse(
        quiz_id=quiz_id,
        title=quiz_dict["title"],
        filename=quiz_dict["filename"],
        question_count=quiz_dict["question_count"],
        uploaded_at=uploaded_at,
    )


@router.get("/quizzes", response_model=list[QuizSummary])
def list_quizzes():
    from services.storage import QUIZZES_DIR

    if not QUIZZES_DIR.exists():
        return []

    summaries = []
    for path in QUIZZES_DIR.glob("*.json"):
        data = storage.read_json(path)
        if not data:
            continue  # skip malformed / empty files
        try:
            summaries.append(
                QuizSummary(
                    id=data["id"],
                    title=data["title"],
                    filename=data["filename"],
                    uploaded_at=data["uploaded_at"],
                    question_count=data["question_count"],
                )
            )
        except (KeyError, TypeError):
            # malformed file — skip silently
            continue

    summaries.sort(key=lambda q: q.uploaded_at, reverse=True)
    return summaries


@router.get("/quizzes/{quiz_id}")
def get_quiz(quiz_id: str):
    data = storage.read_json(storage.quiz_path(quiz_id))
    if not data:
        raise HTTPException(status_code=404, detail=f"Quiz '{quiz_id}' not found")
    return data


@router.delete("/quizzes/{quiz_id}")
def delete_quiz(quiz_id: str):
    quiz_file = storage.quiz_path(quiz_id)
    if not quiz_file.exists():
        raise HTTPException(status_code=404, detail=f"Quiz '{quiz_id}' not found")

    # Step 2 — delete quiz file
    quiz_file.unlink()

    # Step 3 — delete attempts file (ignore if missing)
    attempts_file = storage.attempts_path(quiz_id)
    if attempts_file.exists():
        attempts_file.unlink()

    # Step 4 — clean starred.json
    starred = storage.read_json(storage.starred_path())
    storage.write_json(
        storage.starred_path(),
        [e for e in starred if e.get("quiz_id") != quiz_id],
    )

    # Step 5 — clean wrong.json
    wrong = storage.read_json(storage.wrong_path())
    storage.write_json(
        storage.wrong_path(),
        [e for e in wrong if e.get("quiz_id") != quiz_id],
    )

    return {"success": True, "quiz_id": quiz_id}
