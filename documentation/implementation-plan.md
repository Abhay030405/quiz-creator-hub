# Quiz App — Implementation Plan

> This document breaks the build into 5 sequential phases.  
> Each phase is self-contained and ends with a working, testable milestone.  
> Do not start a phase until the previous one is fully working.

---

## Phase Overview

| Phase | Name | What you build | Milestone |
|---|---|---|---|
| 1 | Foundation | Project setup, MD parser, core backend | Backend parses a `.md` file and returns JSON via API |
| 2 | Quiz Engine | Upload, quiz storage, attempts, scoring | You can take a quiz and see your score |
| 3 | React Frontend | All pages, quiz flow, code rendering | Full app works end-to-end in the browser |
| 4 | Starred & Wrong Answers | Bookmarking, wrong answer tracking, review pages | Stars and wrong answer views work |
| 5 | Polish | Dashboard history, UX improvements, edge cases | App feels complete and reliable |

---

## Phase 1 — Foundation

**Goal**: Get the project structure ready and the MD parser working perfectly. This is the most important phase because the parser is the core of the whole app. If the parser is solid, everything else is just plumbing.

**Estimated time**: 1–2 sessions

---

### Step 1.1 — Create the project folder structure

Create the root folder and all subdirectories manually:

```bash
mkdir quiz-app
cd quiz-app
mkdir -p backend/routers backend/services backend/data/quizzes backend/data/attempts
mkdir -p frontend/src/api frontend/src/pages frontend/src/components
```

Create placeholder `__init__.py` files in all backend Python packages:
```bash
touch backend/__init__.py
touch backend/routers/__init__.py
touch backend/services/__init__.py
```

Create empty data files so the app doesn't crash on first run:
```bash
echo "[]" > backend/data/starred.json
echo "[]" > backend/data/wrong.json
```

Create a `.gitignore` at the root:
```
backend/venv/
backend/data/
frontend/node_modules/
frontend/dist/
__pycache__/
*.pyc
.env
```

> **Why ignore `data/`?**: Your quiz data, attempts, and starred questions are personal runtime data — not source code. Don't commit it to Git.

---

### Step 1.2 — Set up the Python backend environment

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
```

Create `requirements.txt`:
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
```

Install:
```bash
pip install -r requirements.txt
```

---

### Step 1.3 — Write `services/storage.py`

This is a helper module that handles all file I/O. Every read/write of JSON goes through here. This centralises error handling so the rest of the code is clean.

**Functions to implement:**

```python
def ensure_data_dirs():
    """
    Called once on app startup.
    Creates backend/data/, backend/data/quizzes/, backend/data/attempts/
    Creates starred.json and wrong.json with [] if they don't exist.
    """

def read_json(filepath: str) -> dict | list:
    """
    Read and parse a JSON file. Returns empty dict or list if file doesn't exist.
    Raises an exception if the file exists but is not valid JSON.
    """

def write_json(filepath: str, data: dict | list) -> None:
    """
    Serialize data to JSON and write to filepath.
    Use indent=2 for human-readable output (helps with debugging).
    Creates parent directories if they don't exist.
    """

def quiz_path(quiz_id: str) -> str:
    """Returns 'backend/data/quizzes/{quiz_id}.json'"""

def attempts_path(quiz_id: str) -> str:
    """Returns 'backend/data/attempts/{quiz_id}.json'"""
```

**Important**: Use `pathlib.Path` instead of string concatenation for all paths. It's cross-platform (works on Windows too).

---

### Step 1.4 — Write `services/md_parser.py`

This is the heart of the backend. Write it carefully and test it thoroughly.

**The function signature:**

```python
def parse_quiz(raw_text: str, filename: str) -> dict:
    """
    Parse raw Markdown text into a structured quiz dict.
    
    Returns:
        {
            "title": str,
            "filename": str,
            "question_count": int,
            "questions": [ ... ]
        }
    
    Raises:
        ValueError: with a descriptive message if parsing fails
    """
```

**Parsing algorithm — implement it in this exact order:**

**Step A: Extract quiz title**
```python
# Look for the first line starting with "# " (single hash)
# If found, use the text after "# " as the title
# If not found, use the filename (without .md extension) as the title
```

**Step B: Split into question blocks**
```python
# Split the full text by the pattern r'\n## Q\d+'
# This gives you a list of raw question blocks
# The first element (before the first ## Q) is the header — discard it
# Each remaining element is one question's raw text
```

**Step C: For each question block, extract components**

```python
def parse_question(block: str, index: int) -> dict:
    """Parse one question block."""
    
    # 1. Extract code block (if present)
    #    Look for ``` ... ``` using regex
    #    Capture the language (the word right after opening ```)
    #    Capture the content between the fences
    #    Store in code_language and code
    #    Remove the code block from the block text entirely
    
    # 2. Extract options
    #    Look for lines matching ^[A-D]\) (.+)$
    #    Store as dict: {"A": "...", "B": "...", "C": "...", "D": "..."}
    #    Strip the ✓ character if present at the end of an option
    
    # 3. Extract correct answer
    #    Look for the pattern r'\*\*Answer:\s*([A-D])\*\*'
    #    If not found: raise ValueError(f"Question {index+1} is missing **Answer:** line")
    
    # 4. Extract question text
    #    Everything before the first "A)" line is the question text
    #    Strip whitespace, leading/trailing newlines
    
    # 5. Validate
    #    All 4 options (A, B, C, D) must be present
    #    Correct answer must be one of A, B, C, D
    #    Question text must not be empty
    
    return {
        "index": index,
        "text": question_text,
        "code": code or None,
        "code_language": code_language or None,
        "options": options,
        "correct_answer": correct_answer
    }
```

**Step D: Assemble and return**
```python
return {
    "title": title,
    "filename": filename,
    "question_count": len(questions),
    "questions": questions
}
```

**Test the parser manually before moving on:**

Create a `test_parser.py` at the root of backend:
```python
from services.md_parser import parse_quiz

with open("sample_quiz.md", "r") as f:
    raw = f.read()

result = parse_quiz(raw, "sample_quiz.md")
import json
print(json.dumps(result, indent=2))
```

Write a `sample_quiz.md` with 3–4 questions including one with a code block. Run `python test_parser.py` and verify the output JSON is exactly what you expect.

**Do not proceed to Phase 2 until the parser output is perfect.**

---

### Step 1.5 — Write the bare minimum `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.storage import ensure_data_dirs

app = FastAPI(title="Quiz App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    ensure_data_dirs()

@app.get("/")
def health():
    return {"status": "ok"}
```

Start the server: `uvicorn main:app --reload`
Visit `http://localhost:8000/` → you should see `{"status": "ok"}`.

---

### Phase 1 Milestone ✓

By the end of Phase 1 you have:
- All folders created
- Python venv working, deps installed
- `storage.py` reading and writing JSON files correctly
- `md_parser.py` correctly parsing a test MD file into structured JSON
- `main.py` starting with no errors
- Server responds to `GET /` with 200

---

## Phase 2 — Quiz Engine (Backend Complete)

**Goal**: Implement all backend API endpoints. By the end of this phase, the entire backend is done and you can test every API route using FastAPI's built-in docs at `/docs`.

**Estimated time**: 1–2 sessions

---

### Step 2.1 — Implement `routers/quizzes.py`

#### `POST /api/quizzes/upload`

This is the most complex route. Here is the full logic:

```
1. Receive the uploaded file (FastAPI's UploadFile)
2. Check the file extension is .md — if not, return 400
3. Read the raw file content as a string (decode as UTF-8)
4. Call md_parser.parse_quiz(raw_text, filename)
   - If it raises ValueError, return 422 with the error message
5. Generate a quiz_id: use uuid4() and take the first 8 characters
6. Build the full quiz dict:
   - Add "id": quiz_id
   - Add "uploaded_at": datetime.utcnow().isoformat() + "Z"
   - Include everything from the parser output
7. Write to data/quizzes/{quiz_id}.json using storage.write_json()
8. Return: { "quiz_id": quiz_id, "title": title, "question_count": n }
```

#### `GET /api/quizzes`

```
1. List all .json files in data/quizzes/
2. For each file, read it and extract only: id, title, filename, uploaded_at, question_count
   (Do NOT include the questions array — too large for a list response)
3. Sort by uploaded_at descending (newest first)
4. Return the array
```

#### `GET /api/quizzes/{quiz_id}`

```
1. Build the path: data/quizzes/{quiz_id}.json
2. If file doesn't exist, return 404
3. Read and return the full JSON (including all questions and correct_answer fields)
```

#### `DELETE /api/quizzes/{quiz_id}`

```
1. Delete data/quizzes/{quiz_id}.json
2. Delete data/attempts/{quiz_id}.json (if it exists)
3. Remove all starred entries for this quiz_id from starred.json
4. Remove all wrong entries for this quiz_id from wrong.json
5. Return {"success": true}
```

**Register the router in `main.py`:**
```python
from routers import quizzes
app.include_router(quizzes.router, prefix="/api")
```

**Test with FastAPI docs** (`http://localhost:8000/docs`):
- Upload your `sample_quiz.md` → verify the response
- Call `GET /api/quizzes` → verify the quiz appears
- Call `GET /api/quizzes/{quiz_id}` → verify full question data

---

### Step 2.2 — Implement `routers/attempts.py`

#### `POST /api/attempts/{quiz_id}`

This is where scoring happens. Full logic:

```
1. Load the quiz from data/quizzes/{quiz_id}.json
   - If not found, return 404
2. Receive the request body: { "answers": { "0": "B", "1": "A", ... } }
3. Calculate score:
   - For each question index in the quiz:
     - Get correct_answer from the quiz
     - Get user's answer from submitted answers dict (may be missing if unanswered)
     - If they match → score++
     - If they don't match → add to wrong_indices list
4. Calculate percentage = (score / total) * 100, rounded to 1 decimal
5. Build the attempt object:
   {
     "attempt_id": f"atmp_{int(datetime.utcnow().timestamp())}",
     "attempted_at": datetime.utcnow().isoformat() + "Z",
     "score": score,
     "total": total,
     "percentage": percentage,
     "answers": submitted_answers,
     "wrong_indices": wrong_indices
   }
6. Load existing attempts file (or start with empty list)
7. Append new attempt to the list
8. Write back to data/attempts/{quiz_id}.json
9. For each wrong_index, build a wrong_answer entry and append to wrong.json
   (Load wrong.json, append, write back)
10. Return: { attempt_id, score, total, percentage, wrong_indices }
```

#### `GET /api/attempts/{quiz_id}`

```
1. Read data/attempts/{quiz_id}.json
2. If file doesn't exist, return { "quiz_id": quiz_id, "attempts": [] }
3. Return the full attempts list sorted by attempted_at descending
```

#### `GET /api/attempts/{quiz_id}/{attempt_id}`

```
1. Read data/attempts/{quiz_id}.json
2. Find the attempt where attempt.attempt_id == attempt_id
3. If not found, return 404
4. Return the attempt object
```

**Test with FastAPI docs:**
- Submit a fake attempt: `POST /api/attempts/{quiz_id}` with body `{"answers": {"0": "A", "1": "B"}}`
- Verify the response has score/total/percentage/wrong_indices
- Verify the file was written to `data/attempts/{quiz_id}.json`
- Verify `data/wrong.json` has the wrong answer entries

---

### Step 2.3 — Implement `routers/bookmarks.py`

#### `POST /api/star`

```
Request body: { "quiz_id": "abc123", "question_index": 2 }

1. Load starred.json
2. Check if an entry with same quiz_id + question_index already exists
3. If exists → do nothing (idempotent), return {"starred": true}
4. If not exists → append new entry with starred_at timestamp
5. Write back starred.json
6. Return {"starred": true}
```

#### `DELETE /api/star`

```
Request body: { "quiz_id": "abc123", "question_index": 2 }

1. Load starred.json
2. Filter out entries matching quiz_id + question_index
3. Write back
4. Return {"starred": false}
```

#### `GET /api/starred`

```
1. Load starred.json → get list of { quiz_id, question_index } refs
2. For each ref:
   - Load the quiz from data/quizzes/{quiz_id}.json
   - Find the question at question_index
   - Build a rich object: { quiz_id, quiz_title, question_index, question, starred_at }
3. Group by quiz_id (optional, frontend can do this too)
4. Return the enriched list
```

#### `GET /api/wrong`

```
1. Read data/wrong.json
2. Return the full list (already enriched when written in POST /api/attempts)
```

#### `DELETE /api/wrong`

```
1. Write [] to data/wrong.json
2. Return {"cleared": true}
```

---

### Step 2.4 — Wire all routers into `main.py`

```python
from routers import quizzes, attempts, bookmarks

app.include_router(quizzes.router, prefix="/api")
app.include_router(attempts.router, prefix="/api")
app.include_router(bookmarks.router, prefix="/api")
```

---

### Phase 2 Milestone ✓

By the end of Phase 2 you have:
- `POST /api/quizzes/upload` working (parses and stores the quiz)
- `GET /api/quizzes` working (lists all quizzes)
- `GET /api/quizzes/{id}` working (returns full quiz with questions)
- `POST /api/attempts/{id}` working (scores and saves an attempt)
- `GET /api/attempts/{id}` working (lists all attempts for a quiz)
- Star / unstar endpoints working
- `GET /api/starred` returning enriched star data
- `GET /api/wrong` and `DELETE /api/wrong` working
- All routes testable via `http://localhost:8000/docs`
- `data/` folder correctly written after each operation

**You should be able to complete a full quiz session entirely via the /docs UI before moving to Phase 3.**

---

## Phase 3 — React Frontend (Core Quiz Flow)

**Goal**: Build the React app from landing page to results. By the end of this phase you can upload a quiz, take it in the browser, and see your score. Stars and wrong answers UI come in Phase 4.

**Estimated time**: 2–3 sessions

---

### Step 3.1 — Set up the React project

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install react-router-dom react-markdown react-syntax-highlighter axios
```

Configure the Vite dev proxy so API calls to `/api` go to the backend (avoids CORS issues in dev):

**`vite.config.js`:**
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

With this proxy, you can use `/api/...` in your frontend code instead of the full `http://localhost:8000/api/...`. The Vite dev server forwards the requests automatically. Update `src/api/client.js` to use `BASE = "/api"`.

---

### Step 3.2 — Write `src/api/client.js`

Write all API call functions here. Keep them thin — just fetch and return JSON. Error handling is done in the page components.

```javascript
const BASE = "/api"

// Quizzes
export async function uploadQuiz(file) { ... }      // POST /api/quizzes/upload (multipart)
export async function getQuizzes() { ... }           // GET /api/quizzes
export async function getQuiz(quizId) { ... }        // GET /api/quizzes/:id
export async function deleteQuiz(quizId) { ... }     // DELETE /api/quizzes/:id

// Attempts
export async function submitAttempt(quizId, answers) { ... }  // POST /api/attempts/:id
export async function getAttempts(quizId) { ... }              // GET /api/attempts/:id
export async function getAttempt(quizId, attemptId) { ... }   // GET /api/attempts/:id/:aid

// Stars
export async function starQuestion(quizId, questionIndex) { ... }    // POST /api/star
export async function unstarQuestion(quizId, questionIndex) { ... }  // DELETE /api/star
export async function getStarred() { ... }                           // GET /api/starred

// Wrong answers
export async function getWrongAnswers() { ... }    // GET /api/wrong
export async function clearWrongAnswers() { ... }  // DELETE /api/wrong
```

---

### Step 3.3 — Set up routing in `App.jsx`

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Quiz from './pages/Quiz'
import Results from './pages/Results'
import Starred from './pages/Starred'
import WrongAnswers from './pages/WrongAnswers'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/quiz/:quizId" element={<Quiz />} />
          <Route path="/results/:quizId/:attemptId" element={<Results />} />
          <Route path="/starred" element={<Starred />} />
          <Route path="/wrong" element={<WrongAnswers />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
```

---

### Step 3.4 — Build `components/Navbar.jsx`

Simple top navigation bar. Links:
- "Quiz App" (logo/title) → `/`
- "Dashboard" → `/dashboard`
- "Starred" → `/starred`
- "Wrong Answers" → `/wrong`

Use `NavLink` from react-router-dom so the active link is visually highlighted.

Keep it minimal — no hamburger menus, no dropdowns. Just a flat row of links.

---

### Step 3.5 — Build `components/CodeBlock.jsx`

This should be built before the QuestionCard because QuestionCard depends on it.

```jsx
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

export default function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{ position: 'relative', margin: '12px 0' }}>
      <button onClick={handleCopy} style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}>
        {copied ? 'Copied!' : 'Copy'}
      </button>
      <SyntaxHighlighter
        language={language || 'text'}
        style={vscDarkPlus}
        showLineNumbers={true}
        wrapLongLines={false}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}
```

**Test this in isolation** by rendering it in App.jsx with some hardcoded code before continuing.

---

### Step 3.6 — Build `components/QuestionCard.jsx`

Props:
- `question` — the question object from the API
- `questionNumber` — 1-based display number (e.g. "Question 4")
- `totalQuestions` — total count for context
- `selectedOption` — currently selected answer (A/B/C/D or null)
- `onSelect(option)` — called when user clicks an option
- `showAnswer` — boolean: if true, reveal correct/wrong highlighting
- `isStarred` — boolean
- `onToggleStar()` — called when star clicked

Structure:
```
┌─────────────────────────────────────────────┐
│  Q4 of 20                          [★ Star] │
│                                             │
│  Question text rendered here                │
│                                             │
│  [Code block if present]                    │
│                                             │
│  [A]  Option A text                         │
│  [B]  Option B text   ← selected (blue)     │
│  [C]  Option C text                         │
│  [D]  Option D text                         │
└─────────────────────────────────────────────┘
```

Option button states:
- Default: gray border, white background
- Selected (during quiz): blue border, light blue background
- Correct (in results view, `showAnswer=true`): green border, light green background
- Wrong (your selected wrong answer, `showAnswer=true`): red border, light red background

---

### Step 3.7 — Build `components/ProgressBar.jsx`

Props: `current`, `total`, `answeredCount`

```
Question 4 of 20          [████████░░░░░░░░░░░░] 8 / 20 answered
```

Simple HTML + CSS. The filled portion is `(answeredCount / total) * 100%`.

---

### Step 3.8 — Build `pages/Home.jsx`

**Layout:**
```
┌────────────────────────────────────────────────┐
│           Quiz App                             │
│   Practice CS Theory MCQs                      │
│                                                │
│   ┌──────────────────────────────────────┐    │
│   │                                      │    │
│   │     Drop your .md quiz file here     │    │
│   │        or click to browse            │    │
│   │                                      │    │
│   └──────────────────────────────────────┘    │
│                                                │
│   [Uploading... spinner]  ← conditional       │
│   [Error message]         ← conditional       │
│                                                │
│   Quiz loaded: "DBMS Normalisation" (25 Qs)   │
│   [Start Quiz →]          ← conditional       │
│                                                │
│   → Go to Dashboard to see all your quizzes   │
└────────────────────────────────────────────────┘
```

**Drag and drop implementation:**

Use the native HTML drag-and-drop events: `onDragOver`, `onDrop`. On drop, extract `event.dataTransfer.files[0]`. Check that the file extension is `.md`. If valid, call `uploadQuiz(file)` from the API client.

Alternatively use `<input type="file" accept=".md">` — simpler and also works.

---

### Step 3.9 — Build `pages/Quiz.jsx`

This is the most complex page. Plan it carefully before coding.

**State:**
```javascript
const [quiz, setQuiz] = useState(null)           // full quiz data
const [currentIndex, setCurrentIndex] = useState(0)
const [answers, setAnswers] = useState({})        // { "0": "B", "2": "A" }
const [starred, setStarred] = useState(new Set()) // Set of starred question indices
const [submitting, setSubmitting] = useState(false)
const [loading, setLoading] = useState(true)
```

**On mount:**
```javascript
// Load quiz + load existing starred questions for this quiz
const quiz = await getQuiz(quizId)
const starredData = await getStarred()
const starredForThisQuiz = new Set(
  starredData
    .filter(s => s.quiz_id === quizId)
    .map(s => s.question_index)
)
setQuiz(quiz)
setStarred(starredForThisQuiz)
```

**Rendering:**
```jsx
<ProgressBar current={currentIndex + 1} total={quiz.question_count} answeredCount={Object.keys(answers).length} />

<QuestionCard
  question={quiz.questions[currentIndex]}
  questionNumber={currentIndex + 1}
  totalQuestions={quiz.question_count}
  selectedOption={answers[currentIndex] || null}
  onSelect={(option) => setAnswers(prev => ({ ...prev, [currentIndex]: option }))}
  showAnswer={false}
  isStarred={starred.has(currentIndex)}
  onToggleStar={() => handleToggleStar(currentIndex)}
/>

<div>
  <button onClick={() => setCurrentIndex(i => i - 1)} disabled={currentIndex === 0}>Previous</button>
  <button onClick={() => setCurrentIndex(i => i + 1)} disabled={currentIndex === quiz.question_count - 1}>Next</button>
  <button onClick={handleSubmit}>Submit Quiz</button>
</div>
```

**Submit logic:**
```javascript
async function handleSubmit() {
  const answered = Object.keys(answers).length
  const total = quiz.question_count
  
  if (answered < total) {
    const confirm = window.confirm(
      `You've answered ${answered} of ${total} questions. Unanswered questions will be marked wrong. Submit anyway?`
    )
    if (!confirm) return
  }
  
  setSubmitting(true)
  const result = await submitAttempt(quizId, answers)
  navigate(`/results/${quizId}/${result.attempt_id}`)
}
```

---

### Step 3.10 — Build `pages/Results.jsx`

**On mount:**
```javascript
// Load both quiz (for question text) and the specific attempt (for answers)
const quiz = await getQuiz(quizId)
const attempt = await getAttempt(quizId, attemptId)
const starredData = await getStarred()
// Pre-populate starred set
```

**Layout:**
```
┌────────────────────────────────────────────────┐
│  DBMS Normalisation                            │
│                                                │
│  Your Score: 18 / 25 (72%)   [green badge]    │
│  Attempted: Jan 10, 2025 at 3:00 PM            │
│                                                │
│  [Retake Quiz]  [Back to Dashboard]            │
│                                                │
│  ─────────────── Question Review ──────────── │
│                                                │
│  Q1 ✓  Which normal form...                   │
│       Your answer: B ✓                        │
│                                                │
│  Q2 ✗  What does this SQL query return?       │
│       [code block]                            │
│       Your answer: A ✗  Correct: C            │
│                                                │
└────────────────────────────────────────────────┘
```

Use `attempt.wrong_indices` (array from the attempt object) to know which questions were wrong. For each question, compare `attempt.answers[index]` with `quiz.questions[index].correct_answer`.

---

### Phase 3 Milestone ✓

By the end of Phase 3 you can:
- Open `http://localhost:5173`
- Upload a `.md` quiz file from the Home page
- Take the quiz question by question in the browser
- See code blocks rendered with syntax highlighting
- Submit and see your score with a full question breakdown
- Use Previous/Next to navigate between questions

---

## Phase 4 — Starred Questions & Wrong Answers

**Goal**: Implement the starred questions feature and the wrong answers review page. These are the "study tools" that make the app genuinely useful for revision, not just testing.

**Estimated time**: 1–2 sessions

---

### Step 4.1 — Wire up the Star button in Quiz.jsx and Results.jsx

The `StarButton` component and the `onToggleStar` handler already exist from Phase 3. Now make it actually call the API.

**In `Quiz.jsx`:**
```javascript
async function handleToggleStar(questionIndex) {
  if (starred.has(questionIndex)) {
    await unstarQuestion(quizId, questionIndex)
    setStarred(prev => { const s = new Set(prev); s.delete(questionIndex); return s })
  } else {
    await starQuestion(quizId, questionIndex)
    setStarred(prev => new Set([...prev, questionIndex]))
  }
}
```

The UI update is optimistic (instant). The API call happens in the background. If it fails, the local state stays changed — acceptable for personal use.

**In `Results.jsx`:**
Same handler, same pattern. Load starred state on mount (already planned in Phase 3 Step 3.10).

---

### Step 4.2 — Build `pages/Starred.jsx`

**On mount:**
```javascript
const starredList = await getStarred()
// API already returns enriched data: { quiz_id, quiz_title, question_index, question, starred_at }
setStarred(starredList)
```

**Layout:**
```
Starred Questions (12 total)

─── DBMS Normalisation ────────────────────────

  [★]  Q2 — What does the following SQL query return?
       [code block: SQL]
       A) ...  B) ...  C) ...  D) ...
       ✓ Correct answer: C

─── OOP Concepts ───────────────────────────────

  [★]  Q5 — Which of the following demonstrates polymorphism?
       A) ...  B) ...  C) ...  D) ...
       ✓ Correct answer: B

```

Group starred questions by `quiz_title`. Within each group, show questions in `question_index` order.

The "unstar" button (the filled star icon) calls `unstarQuestion()` and removes the item from local state immediately.

Show correct answer by default on this page (it's a review page, not a test).

---

### Step 4.3 — Build `pages/WrongAnswers.jsx`

**On mount:**
```javascript
const wrongList = await getWrongAnswers()
// Returns: [{ quiz_id, quiz_title, question_index, question_text, your_answer, correct_answer, attempt_id, attempted_at }]
setWrong(wrongList)
```

**Layout:**
```
Wrong Answers (47 total)

[Filter by quiz: All ▼]   [Clear All ✕]

─── DBMS Normalisation ────────────────────────

  Q2 — Attempted Jan 10, 2025
  What does the following SQL query return?
  [code block]
  Your answer: A (✗)   Correct answer: C (✓)

  Q2 — Attempted Jan 12, 2025   ← same Q, different attempt
  ...same question...
  Your answer: B (✗)   Correct answer: C (✓)

```

**Filter by quiz**: A `<select>` dropdown populated with unique quiz titles from the wrong list. Filtering is done in JS (no API call needed — all data is already loaded).

**Clear all**: calls `clearWrongAnswers()` from the API client. Asks for confirmation first: `window.confirm("This will permanently delete all wrong answer records. Continue?")`. On success, set `wrong` state to `[]`.

**Note**: The same question can appear multiple times if you got it wrong in multiple attempts. This is intentional — it shows you which questions you *keep* getting wrong.

---

### Step 4.4 — Build `pages/Dashboard.jsx`

**On mount:**
```javascript
const quizzes = await getQuizzes()
setQuizzes(quizzes)
// Don't load attempts for all quizzes upfront — lazy load per quiz
```

**Layout:**
```
Your Quizzes                          [+ Upload New]

┌──────────────────────────────────────────────────────────┐
│ DBMS Normalisation               Uploaded: Jan 10        │
│ 25 questions                     Best: 72% (18/25)       │
│                                                          │
│ [Retake Quiz]  [View History ▼]                         │
├──────────────────────────────────────────────────────────┤
│  History:                                                │
│  Jan 12   20/25  80%   [View breakdown →]               │
│  Jan 10   18/25  72%   [View breakdown →]               │
└──────────────────────────────────────────────────────────┘
```

**Lazy loading attempts**: When the user clicks "View History", call `getAttempts(quizId)` and store the result in a local `attemptsMap` state. Subsequent clicks use the cached data.

**Best score**: Calculated from the attempts array: `Math.max(...attempts.map(a => a.percentage))`. Show "No attempts yet" if attempts array is empty.

**"View breakdown →"**: Navigates to `/results/:quizId/:attemptId` (the existing Results page works perfectly for viewing past attempts).

---

### Phase 4 Milestone ✓

By the end of Phase 4 you can:
- Star any question during a quiz or in the results view
- Visit `/starred` and review all starred questions with correct answers shown
- Submit a quiz and automatically see wrong answers accumulate in `/wrong`
- Filter wrong answers by quiz
- Clear all wrong answers
- See all quizzes on the dashboard with attempt history
- Jump to any past attempt's result breakdown

---

## Phase 5 — Polish & Edge Cases

**Goal**: Harden the app, handle edge cases gracefully, improve the UX for the small things that make a big difference in day-to-day use.

**Estimated time**: 1 session

---

### Step 5.1 — Loading states and error handling

Every page that makes API calls on mount should show a loading indicator while waiting. Use a simple pattern:

```jsx
if (loading) return <div>Loading...</div>
if (error) return <div>Error: {error}. <button onClick={retry}>Retry</button></div>
```

Every API call that can fail should have a try/catch. Errors should be surfaced to the user, not silently swallowed.

**Key places to add error handling:**
- `Home.jsx`: upload failure (bad MD format, network error)
- `Quiz.jsx`: failed to load quiz (quiz_id not found)
- `Quiz.jsx`: failed to submit attempt (network error — show "Failed to submit. Try again." without losing answers)
- `Results.jsx`: failed to load attempt

For the submit failure case in `Quiz.jsx`, it's critical that the `answers` state is NOT cleared if submission fails. The user should be able to retry submit without re-answering questions.

---

### Step 5.2 — Empty states

Every list view needs a graceful empty state:

- **Dashboard**: "No quizzes yet. Upload a .md file to get started." with a link to `/`
- **Starred**: "You haven't starred any questions yet. Star questions while taking a quiz."
- **Wrong Answers**: "No wrong answers recorded. Keep taking quizzes!"
- **Attempt History**: "No attempts yet. Take the quiz to see your history."

These make the app feel complete instead of broken.

---

### Step 5.3 — The `ScoreBadge.jsx` component

A reusable badge that shows score with color coding. Used in Dashboard and Results.

```jsx
function ScoreBadge({ score, total, percentage }) {
  const color = percentage >= 70 ? 'green' : percentage >= 50 ? 'orange' : 'red'
  return (
    <span style={{ color, fontWeight: 'bold', fontSize: '1.2rem' }}>
      {score}/{total} ({percentage}%)
    </span>
  )
}
```

---

### Step 5.4 — Quiz question navigation dots (optional but useful)

Below the question card in `Quiz.jsx`, show a row of small circles — one per question. Each dot is:
- White/gray = unanswered
- Blue = answered
- Gold = starred

Clicking a dot jumps to that question: `setCurrentIndex(i)`.

This is particularly useful for longer quizzes (30+ questions) where you want to see which ones you've skipped at a glance.

---

### Step 5.5 — Keyboard navigation in Quiz.jsx

Add keyboard shortcuts so you can navigate without clicking:

```javascript
useEffect(() => {
  function handleKey(e) {
    if (e.key === 'ArrowRight') setCurrentIndex(i => Math.min(i + 1, total - 1))
    if (e.key === 'ArrowLeft')  setCurrentIndex(i => Math.max(i - 1, 0))
    if (e.key === 'a' || e.key === 'A') onSelect('A')
    if (e.key === 'b' || e.key === 'B') onSelect('B')
    if (e.key === 'c' || e.key === 'C') onSelect('C')
    if (e.key === 'd' || e.key === 'D') onSelect('D')
  }
  window.addEventListener('keydown', handleKey)
  return () => window.removeEventListener('keydown', handleKey)
}, [currentIndex, total])
```

This makes the quiz significantly faster to go through. Press A/B/C/D to answer, arrow keys to navigate.

---

### Step 5.6 — Prevent accidental navigation away from an in-progress quiz

If the user has answered at least one question and tries to navigate away (back button, clicking a nav link), warn them:

```javascript
useEffect(() => {
  const hasAnswers = Object.keys(answers).length > 0
  if (!hasAnswers) return
  
  const handleBeforeUnload = (e) => {
    e.preventDefault()
    e.returnValue = ''
  }
  window.addEventListener('beforeunload', handleBeforeUnload)
  return () => window.removeEventListener('beforeunload', handleBeforeUnload)
}, [answers])
```

This triggers the browser's built-in "Leave page? Changes you made may not be saved" dialog.

---

### Step 5.7 — Delete quiz from Dashboard

Add a small delete button (trash icon) on each quiz card in the Dashboard. On click:
- Show `window.confirm("Delete this quiz and all its data? This cannot be undone.")`
- Call `DELETE /api/quizzes/{quiz_id}`
- Remove the quiz from local state immediately
- Show a brief success message

---

### Step 5.8 — Final end-to-end test

Run through this full checklist before considering the app complete:

- [ ] Upload a new `.md` quiz file
- [ ] Upload a file with a bad format → see the error message
- [ ] Take the quiz, skip one question, submit → see the warning
- [ ] Check score is correct
- [ ] Check wrong answers are in `/wrong`
- [ ] Star 2 questions from the results page
- [ ] Check starred questions appear in `/starred`
- [ ] Retake the quiz → see it in history on Dashboard
- [ ] Navigate to a past attempt from Dashboard
- [ ] Kill the backend (`Ctrl+C`)
- [ ] Restart the backend
- [ ] Verify all quizzes, attempts, stars, and wrong answers are still there
- [ ] Open on a second device (phone on same WiFi)
- [ ] Verify all data is visible on the second device

---

### Phase 5 Milestone ✓ — App Complete

By the end of Phase 5 the app:
- Handles all common errors gracefully with user-facing messages
- Has empty states everywhere
- Supports keyboard navigation in the quiz
- Warns before navigating away from an in-progress quiz
- Supports quiz deletion
- Has been tested end-to-end including a server restart
- Works on a second device on the same network

---

## Quick Reference — Build Order Checklist

```
Phase 1 — Foundation
  [_] 1.1  Create folder structure
  [_] 1.2  Set up Python venv and install deps
  [_] 1.3  Write services/storage.py
  [_] 1.4  Write services/md_parser.py (+ test it)
  [_] 1.5  Write bare minimum main.py

Phase 2 — Backend Complete
  [_] 2.1  routers/quizzes.py (upload, list, get, delete)
  [_] 2.2  routers/attempts.py (submit, get all, get one)
  [_] 2.3  routers/bookmarks.py (star, unstar, get starred, wrong answers)
  [_] 2.4  Register all routers in main.py
  [_]      Test all endpoints via /docs

Phase 3 — Frontend Core
  [_] 3.1  Vite project setup + install deps + proxy config
  [_] 3.2  src/api/client.js
  [_] 3.3  App.jsx routing
  [_] 3.4  Navbar.jsx
  [_] 3.5  CodeBlock.jsx (test in isolation)
  [_] 3.6  QuestionCard.jsx
  [_] 3.7  ProgressBar.jsx
  [_] 3.8  Home.jsx (upload page)
  [_] 3.9  Quiz.jsx (quiz flow)
  [_] 3.10 Results.jsx (score + breakdown)

Phase 4 — Starred & Wrong Answers
  [_] 4.1  Wire star API calls in Quiz.jsx and Results.jsx
  [_] 4.2  Starred.jsx
  [_] 4.3  WrongAnswers.jsx
  [_] 4.4  Dashboard.jsx (with lazy-loaded attempt history)

Phase 5 — Polish
  [_] 5.1  Loading states + error handling on all pages
  [_] 5.2  Empty states on all list views
  [_] 5.3  ScoreBadge.jsx component
  [_] 5.4  Question navigation dots
  [_] 5.5  Keyboard navigation (A/B/C/D + arrow keys)
  [_] 5.6  Prevent accidental navigation away from quiz
  [_] 5.7  Delete quiz from Dashboard
  [_] 5.8  Full end-to-end test including server restart
```
