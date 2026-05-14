"""
Phase 2 automated verification — tests all backend routes.
Run from project root: python backend/verify_phase2.py
Requires the backend server running on port 8001.
"""
import json
import sys
from pathlib import Path

import urllib.request
import urllib.error

BASE = "http://localhost:8001"
DATA_DIR = Path(__file__).parent / "data"

SAMPLE_MD = """# Phase 2 Verification Quiz

## Q1
Which normal form eliminates partial dependencies?

A) 1NF
B) 2NF ✓
C) 3NF
D) BCNF

**Answer: B**

---

## Q2
What does ACID stand for in database transactions?

A) Atomicity, Consistency, Isolation, Durability ✓
B) Availability, Consistency, Isolation, Durability
C) Atomicity, Concurrency, Isolation, Durability
D) Atomicity, Consistency, Independence, Durability

**Answer: A**

---

## Q3
Which layer of the OSI model handles routing?

A) Data Link
B) Transport
C) Network ✓
D) Session

**Answer: C**
"""


def request(method: str, path: str, body=None, files=None) -> dict:
    url = BASE + path
    if files:
        # Multipart upload
        import email.mime.multipart
        import io
        boundary = "boundary123456"
        body_bytes = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{files["filename"]}"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f'{files["content"]}\r\n'
            f"--{boundary}--\r\n"
        ).encode()
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
    elif body is not None:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
    else:
        req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": json.loads(e.read())}


def check(condition: bool, msg: str):
    if condition:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ FAIL: {msg}")
        sys.exit(1)


print("=" * 60)
print("Phase 2 Backend Verification")
print("=" * 60)

# Clean up any leftover data from previous test runs
print("\n[0] Resetting test data (clearing wrong.json, starred.json leftovers)")
request("DELETE", "/api/wrong")
# Remove any starred entries that came from leftover quiz IDs
starred = request("GET", "/api/starred")
# Just overwrite starred.json directly since there's no bulk-clear API
(DATA_DIR / "starred.json").write_text("[]")
print("  ✓ Test data reset")

# ---- quizzes ----
print("\n[1] GET /api/quizzes → expect list")
r = request("GET", "/api/quizzes")
check(r["status"] == 200, f"status 200 (got {r['status']})")
check(isinstance(r["body"], list), "returns list")

print("\n[2] POST /api/quizzes/upload → upload sample quiz")
r = request("POST", "/api/quizzes/upload", files={"filename": "verify.md", "content": SAMPLE_MD})
check(r["status"] == 200, f"status 200 (got {r['status']}), body={r['body']}")
check("quiz_id" in r["body"], "response has quiz_id")
check(r["body"]["question_count"] == 3, f"question_count == 3 (got {r['body'].get('question_count')})")
quiz_id = r["body"]["quiz_id"]
print(f"     quiz_id = {quiz_id}")

print("\n[3] GET /api/quizzes → quiz appears in list")
r = request("GET", "/api/quizzes")
check(r["status"] == 200, "status 200")
ids = [q["id"] for q in r["body"]]
check(quiz_id in ids, f"quiz_id {quiz_id} in list")
check("questions" not in r["body"][0], "no questions array in summary")

print("\n[4] GET /api/quizzes/{id} → full quiz with questions")
r = request("GET", f"/api/quizzes/{quiz_id}")
check(r["status"] == 200, "status 200")
check("questions" in r["body"], "has questions array")
check(len(r["body"]["questions"]) == 3, "3 questions")
check("correct_answer" in r["body"]["questions"][0], "correct_answer present")

print("\n[5] POST /api/quizzes/upload with .txt → 400")
r = request("POST", "/api/quizzes/upload", files={"filename": "bad.txt", "content": "hello"})
check(r["status"] == 400, f"status 400 (got {r['status']})")

print("\n[6] POST /api/quizzes/upload with broken MD → 422")
broken_md = "# Broken\n\n## Q1\nWhat is this?\n\nA) X\nB) Y\nC) Z\nD) W\n\n"  # no Answer line
r = request("POST", "/api/quizzes/upload", files={"filename": "broken.md", "content": broken_md})
check(r["status"] == 422, f"status 422 (got {r['status']})")

# ---- attempts ----
print("\n[7] GET /api/attempts/{id} before any attempt → empty list")
r = request("GET", f"/api/attempts/{quiz_id}")
check(r["status"] == 200, "status 200")
check(r["body"]["attempts"] == [], "empty attempts list")

print("\n[8] POST /api/attempts/{id} → submit answers (Q1 correct, Q2 wrong, Q3 correct)")
# Correct: Q1=B, Q2=A, Q3=C — submitting Q2 as wrong
answers = {"0": "B", "1": "D", "2": "C"}
r = request("POST", f"/api/attempts/{quiz_id}", body={"answers": answers})
check(r["status"] == 200, f"status 200 (got {r['status']})")
check(r["body"]["score"] == 2, f"score == 2 (got {r['body'].get('score')})")
check(r["body"]["total"] == 3, f"total == 3 (got {r['body'].get('total')})")
check(1 in r["body"]["wrong_indices"], f"index 1 in wrong_indices (got {r['body'].get('wrong_indices')})")
attempt_id = r["body"]["attempt_id"]
print(f"     attempt_id = {attempt_id}")

print("\n[9] GET /api/attempts/{id} → attempt appears")
r = request("GET", f"/api/attempts/{quiz_id}")
check(r["status"] == 200, "status 200")
check(len(r["body"]["attempts"]) == 1, "1 attempt in list")

print("\n[10] GET /api/attempts/{id}/{attempt_id} → specific attempt")
r = request("GET", f"/api/attempts/{quiz_id}/{attempt_id}")
check(r["status"] == 200, "status 200")
check(r["body"]["attempt_id"] == attempt_id, "correct attempt returned")

print("\n[11] POST /api/attempts with invalid answer value → 400")
r = request("POST", f"/api/attempts/{quiz_id}", body={"answers": {"0": "E"}})
check(r["status"] == 400, f"status 400 (got {r['status']})")

print("\n[12] POST /api/attempts with nonexistent quiz → 404")
r = request("POST", "/api/attempts/xxxxxxxx", body={"answers": {}})
check(r["status"] == 404, f"status 404 (got {r['status']})")

# ---- bookmarks ----
print("\n[13] GET /api/starred → empty")
r = request("GET", "/api/starred")
check(r["status"] == 200, "status 200")
check(r["body"] == [], "empty starred list")

print("\n[14] POST /api/star → star Q1")
r = request("POST", "/api/star", body={"quiz_id": quiz_id, "question_index": 0})
check(r["status"] == 200, "status 200")
check(r["body"]["starred"] is True, "starred == true")

print("\n[15] POST /api/star again (idempotent) → no duplicate")
r = request("POST", "/api/star", body={"quiz_id": quiz_id, "question_index": 0})
check(r["status"] == 200, "status 200 (idempotent)")
starred_json = json.loads(Path("backend/data/starred.json").read_text())
check(sum(1 for e in starred_json if e["quiz_id"] == quiz_id and e["question_index"] == 0) == 1,
      "only one entry in starred.json (no duplicate)")

print("\n[16] GET /api/starred → enriched entry")
r = request("GET", "/api/starred")
check(r["status"] == 200, "status 200")
check(len(r["body"]) == 1, "1 starred item")
check("question" in r["body"][0], "enriched with question object")
check("quiz_title" in r["body"][0], "has quiz_title")

print("\n[17] DELETE /api/star → unstar Q1")
r = request("DELETE", "/api/star", body={"quiz_id": quiz_id, "question_index": 0})
check(r["status"] == 200, "status 200")
check(r["body"]["starred"] is False, "starred == false")

print("\n[18] DELETE /api/star again (idempotent) → no error")
r = request("DELETE", "/api/star", body={"quiz_id": quiz_id, "question_index": 0})
check(r["status"] == 200, "status 200 (idempotent)")

print("\n[19] POST /api/star with nonexistent quiz → 404")
r = request("POST", "/api/star", body={"quiz_id": "zzzzzzzz", "question_index": 0})
check(r["status"] == 404, f"status 404 (got {r['status']})")

print("\n[20] POST /api/star with out-of-range index → 400")
r = request("POST", "/api/star", body={"quiz_id": quiz_id, "question_index": 999})
check(r["status"] == 400, f"status 400 (got {r['status']})")

print("\n[21] GET /api/wrong → enriched wrong answers from attempt")
r = request("GET", "/api/wrong")
check(r["status"] == 200, "status 200")
check(len(r["body"]) >= 1, f"at least 1 wrong entry (got {len(r['body'])})")
check("question_text" in r["body"][0], "has question_text")
check("options" in r["body"][0], "has options")
check("correct_answer" in r["body"][0], "has correct_answer")

print("\n[22] DELETE /api/wrong → clear all wrong answers")
r = request("DELETE", "/api/wrong")
check(r["status"] == 200, "status 200")
check(r["body"]["cleared"] is True, "cleared == true")
r = request("GET", "/api/wrong")
check(r["body"] == [], "wrong is now empty")

print("\n[23] DELETE /api/quizzes/{id} → delete quiz and all data")
r = request("DELETE", f"/api/quizzes/{quiz_id}")
check(r["status"] == 200, "status 200")
r = request("GET", f"/api/quizzes/{quiz_id}")
check(r["status"] == 404, "quiz returns 404 after deletion")
check(not (DATA_DIR / "quizzes" / f"{quiz_id}.json").exists(), "quiz file deleted")
check(not (DATA_DIR / "attempts" / f"{quiz_id}.json").exists(), "attempts file deleted")

print("\n" + "=" * 60)
print("All Phase 2 checks passed!")
print("=" * 60)
