from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import storage

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class StarRequest(BaseModel):
    quiz_id: str
    question_index: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/star")
def star_question(request: StarRequest):
    starred = storage.read_json(storage.starred_path())

    # Step 2 — check for existing entry (idempotent)
    for entry in starred:
        if (
            entry.get("quiz_id") == request.quiz_id
            and entry.get("question_index") == request.question_index
        ):
            return {"starred": True}

    # Step 3 — validate quiz and question_index exist
    quiz = storage.read_json(storage.quiz_path(request.quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail=f"Quiz '{request.quiz_id}' not found")

    if not (0 <= request.question_index < len(quiz["questions"])):
        raise HTTPException(
            status_code=400,
            detail=f"Question index {request.question_index} is out of range for this quiz",
        )

    # Step 4 — append and write
    new_entry = {
        "quiz_id": request.quiz_id,
        "question_index": request.question_index,
        "starred_at": datetime.utcnow().isoformat() + "Z",
    }
    starred.append(new_entry)
    storage.write_json(storage.starred_path(), starred)

    return {"starred": True}


@router.delete("/star")
def unstar_question(request: StarRequest):
    starred = storage.read_json(storage.starred_path())
    filtered = [
        e
        for e in starred
        if not (
            e.get("quiz_id") == request.quiz_id
            and e.get("question_index") == request.question_index
        )
    ]
    storage.write_json(storage.starred_path(), filtered)
    return {"starred": False}


@router.get("/starred")
def get_starred():
    starred = storage.read_json(storage.starred_path())
    if not starred:
        return []

    # Group by quiz_id to avoid loading the same quiz file multiple times
    quiz_map: dict[str, dict] = {}
    for entry in starred:
        qid = entry.get("quiz_id")
        if qid and qid not in quiz_map:
            quiz_data = storage.read_json(storage.quiz_path(qid))
            quiz_map[qid] = quiz_data if quiz_data else None  # None = deleted

    enriched = []
    orphaned_keys: set[tuple] = set()

    for entry in starred:
        qid = entry.get("quiz_id")
        q_index = entry.get("question_index")
        quiz = quiz_map.get(qid)

        if not quiz:
            # Quiz was deleted — mark as orphaned
            orphaned_keys.add((qid, q_index))
            continue

        questions = quiz.get("questions", [])
        if q_index is None or q_index < 0 or q_index >= len(questions):
            orphaned_keys.add((qid, q_index))
            continue

        enriched.append(
            {
                "quiz_id": qid,
                "quiz_title": quiz["title"],
                "question_index": q_index,
                "question": questions[q_index],
                "starred_at": entry.get("starred_at"),
            }
        )

    # Clean up orphaned entries
    if orphaned_keys:
        cleaned = [
            e
            for e in starred
            if (e.get("quiz_id"), e.get("question_index")) not in orphaned_keys
        ]
        storage.write_json(storage.starred_path(), cleaned)

    enriched.sort(key=lambda e: e["starred_at"] or "", reverse=True)
    return enriched


@router.get("/wrong")
def get_wrong():
    wrong = storage.read_json(storage.wrong_path())
    return sorted(wrong, key=lambda e: e.get("attempted_at", ""), reverse=True)


@router.delete("/wrong")
def clear_wrong():
    storage.write_json(storage.wrong_path(), [])
    return {"cleared": True, "message": "All wrong answers have been cleared"}
