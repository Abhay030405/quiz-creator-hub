import json
import os
import tempfile
from pathlib import Path

# All paths are anchored to the backend/ directory
_BASE = Path(__file__).parent.parent  # backend/

DATA_DIR = _BASE / "data"
QUIZZES_DIR = DATA_DIR / "quizzes"
ATTEMPTS_DIR = DATA_DIR / "attempts"
STARRED_FILE = DATA_DIR / "starred.json"
WRONG_FILE = DATA_DIR / "wrong.json"


def ensure_data_dirs() -> None:
    """
    Called once on app startup. Creates all required data directories and
    initialises starred.json and wrong.json with [] if they don't exist.
    """
    QUIZZES_DIR.mkdir(parents=True, exist_ok=True)
    ATTEMPTS_DIR.mkdir(parents=True, exist_ok=True)

    if not STARRED_FILE.exists():
        write_json(STARRED_FILE, [])

    if not WRONG_FILE.exists():
        write_json(WRONG_FILE, [])


def read_json(filepath: Path) -> dict | list:
    """
    Read and parse a JSON file.
    Returns [] for list files and {} for dict files if the file doesn't exist.
    Raises ValueError if the file exists but contains invalid JSON.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        # List files: starred.json, wrong.json, attempts per quiz
        # Dict files: quiz data files
        if filepath.parent == QUIZZES_DIR:
            return {}
        return []
    try:
        with filepath.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {filepath}: {exc}") from exc


def write_json(filepath: Path, data: dict | list) -> None:
    """
    Atomically write data as JSON to filepath (write to temp file, then rename).
    Creates parent directories if they don't exist.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp file in the same directory, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def quiz_path(quiz_id: str) -> Path:
    """Returns the Path to data/quizzes/{quiz_id}.json"""
    return QUIZZES_DIR / f"{quiz_id}.json"


def attempts_path(quiz_id: str) -> Path:
    """Returns the Path to data/attempts/{quiz_id}.json"""
    return ATTEMPTS_DIR / f"{quiz_id}.json"
