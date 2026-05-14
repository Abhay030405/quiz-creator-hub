# Quiz App — Build Plan

> **Purpose**: A personal MCQ practice tool for CS theory subjects (OOP, DBMS, CN, OS, ML, Agentic AI).  
> **Stack**: FastAPI (Python) · React (Vite) · Flat JSON files on disk  
> **Audience**: Personal use only — no auth, no multi-tenancy, no production hardening required.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [MD File Format Specification](#3-md-file-format-specification)
4. [Backend — FastAPI](#4-backend--fastapi)
   - 4.1 Directory Structure
   - 4.2 Data Storage Design
   - 4.3 MD Parser Service
   - 4.4 API Endpoints (all routes)
   - 4.5 CORS & Server Config
5. [Frontend — React](#5-frontend--react)
   - 5.1 Directory Structure
   - 5.2 Routing Plan
   - 5.3 Pages (detailed)
   - 5.4 Components (detailed)
   - 5.5 API Client Layer
   - 5.6 State Management
6. [Feature Specifications](#6-feature-specifications)
   - 6.1 Upload & Parse
   - 6.2 Quiz Flow (question-by-question)
   - 6.3 Code Rendering
   - 6.4 Scoring & Attempts History
   - 6.5 Starred Questions
   - 6.6 Wrong Answers Tracker
   - 6.7 Persistence Across Restarts
7. [Data Schemas (JSON)](#7-data-schemas-json)
8. [Dependencies](#8-dependencies)
9. [Environment & Running Locally](#9-environment--running-locally)
10. [Folder Structure (Full)](#10-folder-structure-full)
11. [Edge Cases & Constraints](#11-edge-cases--constraints)
12. [Future Enhancements (Optional)](#12-future-enhancements-optional)

---

## 1. Project Overview

### What this app does

You write a Markdown file containing MCQs — with questions, A/B/C/D options, optional code blocks, and correct answers marked inside the file. You upload that file to the app. The app parses it, stores it, and gives you a question-by-question quiz interface. At the end you see your score. Every attempt is saved. You can retake any quiz as many times as you want. You can star questions you find important. Wrong answers from every attempt are stored in one place for review.

### Why this design

- **No database**: All data is flat JSON files on disk. Fast to build, zero config, zero migrations. For personal use with a small number of quiz files this is perfectly sufficient.
- **No login**: It's just you. One user, one machine (or same LAN). No privacy concerns.
- **Persistence across restarts**: Data lives on disk, not in memory or browser storage. If the server goes down and comes back up, everything is exactly as you left it.
- **Cross-device**: Since the backend holds all the data, any device that can reach the backend URL will see all the same quizzes, attempts, stars, and wrong answers.

### Subjects this will cover

- Object-Oriented Programming (OOP)
- Database Management Systems (DBMS)
- Computer Networks (CN)
- Operating Systems (OS)
- Machine Learning theory (ML)
- Agentic AI

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Your Browser / Device                       │
│                                                                      │
│   React App (Vite, port 5173)                                        │
│   ├── Pages: Home, Dashboard, Quiz, Results, Starred, Wrong         │
│   ├── react-markdown + react-syntax-highlighter (code blocks)        │
│   └── All API calls via src/api/client.js                            │
└───────────────────────┬──────────────────────────────────────────────┘
                        │  HTTP / REST (JSON)
                        │  axios or fetch
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (port 8000)                      │
│                                                                      │
│   main.py            → app entry, CORS, router registration          │
│   routers/           → quizzes.py, attempts.py, bookmarks.py         │
│   services/          → md_parser.py (pure Python, no deps)           │
└───────────────────────┬──────────────────────────────────────────────┘
                        │  Read / Write JSON files
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     backend/data/  (disk)                            │
│                                                                      │
│   quizzes/           → one JSON file per uploaded quiz               │
│   attempts/          → one JSON file per quiz, list of all attempts  │
│   starred.json       → flat list of starred question refs            │
│   wrong.json         → flat list of wrong answer refs                │
└─────────────────────────────────────────────────────────────────────┘
```

### Why not use localStorage?

localStorage is browser-specific and device-specific. If you open the app on your phone, it won't see what's in your laptop's localStorage. Since the goal is same-data-everywhere, the backend disk is the single source of truth.

---

## 3. MD File Format Specification

This is the format you must follow when writing your quiz `.md` files. The parser on the backend is built against this spec exactly.

### Full example

```markdown
# DBMS MCQ Quiz — Normalisation

## Q1
Which normal form eliminates partial dependencies?

A) 1NF
B) 2NF ✓
C) 3NF
D) BCNF

**Answer: B**

---

## Q2
What does the following SQL query return?

```sql
SELECT department, COUNT(*) as emp_count
FROM employees
GROUP BY department
HAVING COUNT(*) > 5;
```

A) All employees in departments with more than 5 employees
B) Count of all employees grouped by department
C) Departments that have more than 5 employees, with their count ✓
D) Employees whose count exceeds 5

**Answer: C**

---

## Q3
Which of the following is NOT a property of a transaction? (ACID)

A) Atomicity
B) Consistency
C) Isolation
D) Dependency ✓

**Answer: D**
```

### Parsing rules (what the backend reads)

| Element | Rule |
|---|---|
| Quiz title | First `#` heading in the file (optional, falls back to filename) |
| Question delimiter | `## Q{n}` — must start with `## Q` |
| Question body | All text between the `## Q{n}` line and the first `A)` option |
| Code block | Standard fenced code block (` ```lang `) inside the question body |
| Options | Lines starting with `A)`, `B)`, `C)`, `D)` |
| Correct answer marker | `✓` at the end of the correct option line (optional visual aid) |
| Answer declaration | `**Answer: X**` where X is the letter — this is what the parser reads |
| Question separator | `---` (optional but recommended for readability) |

### Important notes for writing quiz files

- The `**Answer: X**` line is mandatory for every question. Without it the parser will throw an error for that question.
- You can put a code block anywhere in the question body — before or after the text.
- Options must be on their own lines starting with exactly `A)`, `B)`, `C)`, `D)`.
- The `✓` marker on the option line is just for your own reading convenience and is ignored by the parser. The parser only reads `**Answer: X**`.
- Questions are numbered automatically from 1. The `## Q1`, `## Q2` labels are just for human readability.
- You can have any number of questions per file. No upper limit enforced.

---

## 4. Backend — FastAPI

### 4.1 Directory Structure

```
backend/
├── main.py
├── requirements.txt
├── .env                        (optional, for port config)
│
├── routers/
│   ├── __init__.py
│   ├── quizzes.py              (upload, list, get single quiz)
│   ├── attempts.py             (save attempt, get history, get scores)
│   └── bookmarks.py            (star/unstar, get starred, get wrong answers)
│
├── services/
│   ├── __init__.py
│   ├── md_parser.py            (parse raw .md text → structured JSON)
│   └── storage.py              (read/write JSON files, helper functions)
│
└── data/
    ├── quizzes/                (auto-created on first run)
    ├── attempts/               (auto-created on first run)
    ├── starred.json            (auto-created on first run)
    └── wrong.json              (auto-created on first run)
```

### 4.2 Data Storage Design

All data is plain JSON. No SQLite, no Postgres, nothing to install or migrate.

#### `data/quizzes/{quiz_id}.json`

One file per uploaded quiz. Contains the full parsed content including all questions, all options, and the correct answers.

```json
{
  "id": "a3f9c2b1",
  "title": "DBMS MCQ Quiz — Normalisation",
  "subject": "DBMS",
  "filename": "dbms_normalisation.md",
  "uploaded_at": "2025-01-10T14:30:00Z",
  "question_count": 25,
  "questions": [
    {
      "index": 0,
      "text": "Which normal form eliminates partial dependencies?",
      "code": null,
      "code_language": null,
      "options": {
        "A": "1NF",
        "B": "2NF",
        "C": "3NF",
        "D": "BCNF"
      },
      "correct_answer": "B"
    },
    {
      "index": 1,
      "text": "What does the following SQL query return?",
      "code": "SELECT department, COUNT(*) as emp_count\nFROM employees\nGROUP BY department\nHAVING COUNT(*) > 5;",
      "code_language": "sql",
      "options": {
        "A": "All employees in departments with more than 5 employees",
        "B": "Count of all employees grouped by department",
        "C": "Departments that have more than 5 employees, with their count",
        "D": "Employees whose count exceeds 5"
      },
      "correct_answer": "C"
    }
  ]
}
```

#### `data/attempts/{quiz_id}.json`

One file per quiz. Contains a list of every attempt ever made on that quiz.

```json
{
  "quiz_id": "a3f9c2b1",
  "attempts": [
    {
      "attempt_id": "atmp_001",
      "attempted_at": "2025-01-10T15:00:00Z",
      "score": 18,
      "total": 25,
      "percentage": 72.0,
      "answers": {
        "0": "B",
        "1": "A",
        "2": "D"
      },
      "wrong_indices": [1, 2]
    }
  ]
}
```

#### `data/starred.json`

A single flat file. Contains all starred question references across all quizzes.

```json
[
  { "quiz_id": "a3f9c2b1", "question_index": 1, "starred_at": "2025-01-10T16:00:00Z" },
  { "quiz_id": "b7e1d4a2", "question_index": 4, "starred_at": "2025-01-11T09:30:00Z" }
]
```

#### `data/wrong.json`

A single flat file. Aggregated wrong answers across all quizzes and all attempts. Updated after every attempt submission.

```json
[
  {
    "quiz_id": "a3f9c2b1",
    "quiz_title": "DBMS MCQ Quiz — Normalisation",
    "question_index": 1,
    "question_text": "What does the following SQL query return?",
    "your_answer": "A",
    "correct_answer": "C",
    "attempt_id": "atmp_001",
    "attempted_at": "2025-01-10T15:00:00Z"
  }
]
```

### 4.3 MD Parser Service (`services/md_parser.py`)

This is the most important piece of backend logic. It takes the raw text of an uploaded `.md` file and returns a structured list of question objects.

**Algorithm (step by step):**

1. Read the raw file text.
2. Extract the quiz title from the first `#` heading. If none found, use the filename.
3. Split the text by `## Q` to get individual question blocks.
4. For each question block:
   a. Extract everything before the first `A)` as the question body.
   b. Scan the question body for a fenced code block (` ```lang ... ``` `). If found, extract the language and code content. Remove the code block from the plain text portion.
   c. Strip the remaining text → that's `question.text`.
   d. Extract lines starting with `A)`, `B)`, `C)`, `D)` → that's the options dict.
   e. Find the line matching `**Answer: X**` → that's `correct_answer`.
   f. If any mandatory field is missing, raise a `ParseError` with the question number.
5. Return list of question dicts + quiz metadata.

**What it handles:**
- Code blocks anywhere in the question body (before text, after text, between text)
- Multi-line code blocks
- Options with long text (wrapped in the MD but on one logical line)
- The `✓` character on option lines (stripped before storing)
- Windows-style `\r\n` line endings

**What it does NOT handle (by design):**
- Multiple correct answers (this is single-choice MCQ only)
- Images in questions
- More than 4 options (A/B/C/D only)

### 4.4 API Endpoints

#### Quizzes Router (`routers/quizzes.py`)

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| `POST` | `/api/quizzes/upload` | Upload and parse a `.md` file | `multipart/form-data` with `file` field | `{ quiz_id, title, question_count }` |
| `GET` | `/api/quizzes` | List all uploaded quizzes | — | Array of `{ id, title, subject, uploaded_at, question_count }` |
| `GET` | `/api/quizzes/{quiz_id}` | Get full quiz with all questions | — | Full quiz JSON (questions included, correct answers included) |
| `DELETE` | `/api/quizzes/{quiz_id}` | Delete a quiz and all its data | — | `{ success: true }` |

> **Note:** The frontend receives correct answers as part of the full quiz JSON. It stores them in component state and only reveals the answer after the user submits. This is fine for personal use — no cheating concern since it's just you.

#### Attempts Router (`routers/attempts.py`)

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| `POST` | `/api/attempts/{quiz_id}` | Save a completed attempt | `{ answers: { "0": "B", "1": "A", ... } }` | `{ attempt_id, score, total, percentage, wrong_indices }` |
| `GET` | `/api/attempts/{quiz_id}` | Get all attempts for a quiz | — | `{ quiz_id, attempts: [...] }` |
| `GET` | `/api/attempts/{quiz_id}/{attempt_id}` | Get one specific attempt detail | — | Full attempt object |

**How scoring works on the backend:**

When `POST /api/attempts/{quiz_id}` is called:
1. Load the quiz from `data/quizzes/{quiz_id}.json` to get correct answers.
2. Compare submitted answers vs correct answers.
3. Calculate `score`, `total`, `percentage`.
4. Collect `wrong_indices` (list of question indices answered incorrectly).
5. Append the attempt to `data/attempts/{quiz_id}.json`.
6. For each wrong index, append an entry to `data/wrong.json`.
7. Return the result to the frontend.

#### Bookmarks Router (`routers/bookmarks.py`)

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| `POST` | `/api/star` | Star a question | `{ quiz_id, question_index }` | `{ starred: true }` |
| `DELETE` | `/api/star` | Unstar a question | `{ quiz_id, question_index }` | `{ starred: false }` |
| `GET` | `/api/starred` | Get all starred questions with full content | — | Array of `{ quiz_id, quiz_title, question_index, question, starred_at }` |
| `GET` | `/api/wrong` | Get all wrong answers with full content | — | Array of wrong answer objects |
| `DELETE` | `/api/wrong` | Clear all wrong answers | — | `{ cleared: true }` |

### 4.5 CORS & Server Config (`main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Quiz App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For LAN access (phone on same WiFi), add your local IP to `allow_origins`:
```python
allow_origins=["http://localhost:5173", "http://192.168.1.x:5173"]
```

---

## 5. Frontend — React

### 5.1 Directory Structure

```
frontend/
├── package.json
├── vite.config.js
├── index.html
│
└── src/
    ├── main.jsx                (ReactDOM.createRoot, BrowserRouter)
    ├── App.jsx                 (Route definitions)
    │
    ├── api/
    │   └── client.js           (all API functions in one place)
    │
    ├── pages/
    │   ├── Home.jsx            (landing page + file upload)
    │   ├── Dashboard.jsx       (all quizzes list + per-quiz history)
    │   ├── Quiz.jsx            (question-by-question interface)
    │   ├── Results.jsx         (score + breakdown after submission)
    │   ├── Starred.jsx         (all starred questions across quizzes)
    │   └── WrongAnswers.jsx    (all wrong answers across quizzes)
    │
    └── components/
        ├── Navbar.jsx              (top nav with links)
        ├── QuestionCard.jsx        (renders one question + options)
        ├── MarkdownRenderer.jsx    (renders question text as markdown)
        ├── CodeBlock.jsx           (syntax-highlighted code block)
        ├── ProgressBar.jsx         (Q 3 of 20 progress indicator)
        ├── StarButton.jsx          (toggle star icon on a question)
        ├── AttemptHistoryCard.jsx  (shows one attempt row: score, date, %)
        └── ScoreBadge.jsx          (color-coded score display)
```

### 5.2 Routing Plan

```
/                       → Home.jsx          (upload + link to dashboard)
/dashboard              → Dashboard.jsx     (all quizzes, attempt history per quiz)
/quiz/:quizId           → Quiz.jsx          (active quiz session)
/results/:quizId/:attemptId → Results.jsx   (post-quiz score screen)
/starred                → Starred.jsx       (all starred questions)
/wrong                  → WrongAnswers.jsx  (all wrong answers)
```

### 5.3 Pages (Detailed)

#### `Home.jsx`

**Purpose**: Entry point. Upload a new `.md` file or navigate to an existing quiz.

**What it renders:**
- App title + short description
- A large drag-and-drop upload zone (also clickable to open file picker)
- File type validation: only `.md` files accepted
- Upload progress indicator
- On success: show quiz title + question count + "Start Quiz" button
- On error: show the parse error message from the backend (e.g. "Question 3 is missing **Answer:**")
- A "Go to Dashboard →" link to see all past quizzes

**State:**
- `uploading: boolean`
- `uploadError: string | null`
- `uploadedQuiz: { id, title, question_count } | null`

**Behaviour:**
- File dropped or selected → immediately call `POST /api/quizzes/upload`
- If successful → show the quiz card with Start Quiz button
- Navigate to `/quiz/:quizId` on Start Quiz click
- Allow uploading the same file again (creates a new quiz entry each time — no dedup by design)

---

#### `Dashboard.jsx`

**Purpose**: Central hub. See all uploaded quizzes, all attempts, and jump into any quiz.

**What it renders:**
- A card grid of all quizzes, each showing:
  - Quiz title
  - Subject tag (DBMS, OOP, etc.)
  - Question count
  - Upload date
  - Best score (across all attempts)
  - Latest attempt date
  - "Start / Retake" button
  - "View History" expandable section showing all attempts as a table
- Quick links in the sidebar or header: "Starred Questions", "Wrong Answers"

**State:**
- `quizzes: Quiz[]`
- `attemptsMap: { [quiz_id]: Attempt[] }` (loaded lazily when expanded)
- `loading: boolean`

**Behaviour:**
- On mount: `GET /api/quizzes` to load all quizzes
- On "View History" expand: `GET /api/attempts/:quiz_id` (only if not already loaded)
- Clicking "Start Quiz" navigates to `/quiz/:quizId`
- Clicking a specific past attempt navigates to `/results/:quizId/:attemptId`

---

#### `Quiz.jsx`

**Purpose**: The core quiz experience. Shows one question at a time, lets you answer and navigate.

**What it renders:**
- Top: Progress bar (`Question 4 of 20`) + quiz title
- Center: `QuestionCard` component with the current question
- Bottom: Previous / Next / Submit buttons
- Star button on each question (top-right of card)
- Question navigation dots (click to jump to any question) — optional

**State:**
- `quiz: Quiz` (full quiz loaded once on mount)
- `currentIndex: number`
- `answers: { [index]: string }` (user's selected options)
- `starred: Set<number>` (which question indices are starred)
- `submitting: boolean`

**Behaviour:**
- On mount: `GET /api/quizzes/:quizId`, then `GET /api/starred` (to pre-populate starred state)
- Selecting an option updates `answers[currentIndex]`
- Next/Prev buttons change `currentIndex`
- Star button calls `POST /api/star` or `DELETE /api/star` and updates local starred set
- "Submit Quiz" button: only enabled once all questions answered (or allow partial submit with warning)
- On submit: `POST /api/attempts/:quizId` with all answers → navigate to `/results/:quizId/:attemptId`
- Answers are NOT stored in localStorage — if you refresh mid-quiz, you lose progress (acceptable for personal use)

**Submit confirmation**: A simple `window.confirm("Submit quiz? You've answered X of Y questions.")` is enough.

---

#### `Results.jsx`

**Purpose**: Show the outcome of a completed attempt.

**What it renders:**
- Big score display: `18 / 25 (72%)`
- Color-coded: green ≥ 70%, yellow 50–69%, red < 50%
- Time taken (calculated from attempt timestamps if stored)
- A full question-by-question breakdown:
  - For each question: question text + code (if any)
  - Your answer (highlighted green if correct, red if wrong)
  - Correct answer shown for wrong ones
  - Star button on each question
- "Retake Quiz" button → back to `/quiz/:quizId`
- "Back to Dashboard" button

**State:**
- `quiz: Quiz` (loaded to show question text)
- `attempt: Attempt` (loaded by attempt_id)
- `starred: Set<number>`

---

#### `Starred.jsx`

**Purpose**: Review all questions you've starred across all quizzes.

**What it renders:**
- Grouped by quiz (quiz title as section header)
- Each question shown with full text, code block if any, and the correct answer
- Unstar button on each (calls `DELETE /api/star`)
- Empty state: "No starred questions yet. Star questions during a quiz or in results."

---

#### `WrongAnswers.jsx`

**Purpose**: Review every question you've ever gotten wrong, across all quizzes and all attempts.

**What it renders:**
- Filter bar: filter by quiz, filter by date range
- Each wrong answer card shows:
  - Quiz name + date of that attempt
  - Full question text + code block
  - Your answer (red) vs correct answer (green)
  - Star button
- "Clear all wrong answers" button with confirmation
- Empty state: "No wrong answers recorded yet."

---

### 5.4 Components (Detailed)

#### `QuestionCard.jsx`

Props: `question`, `selectedOption`, `onSelect`, `isStarred`, `onToggleStar`, `showAnswer` (boolean, for results view)

Renders:
- Question number badge
- `<MarkdownRenderer>` for question text
- `<CodeBlock>` if `question.code` is not null
- Four option buttons (A/B/C/D)
- Option buttons are highlighted when selected
- If `showAnswer=true`: correct answer gets green highlight, wrong selection gets red
- `<StarButton>` in the top-right corner

---

#### `MarkdownRenderer.jsx`

Wraps `react-markdown`. Renders question text which may contain inline code, bold, italics. Does NOT render code blocks (those are handled separately by `CodeBlock.jsx` using the `code` field from the question JSON, not from the markdown text).

---

#### `CodeBlock.jsx`

Props: `code: string`, `language: string`

Uses `react-syntax-highlighter` with the `vs2015` or `atomDark` theme. Renders the code block with:
- Language label in the top-right corner
- Copy button
- Line numbers
- Horizontal scroll for long lines

---

#### `ProgressBar.jsx`

Props: `current: number`, `total: number`, `answeredCount: number`

Renders:
- `Question {current} of {total}` text
- A colored progress bar (filled = answered questions, not just visited)
- Answered count: `{answeredCount} / {total} answered`

---

#### `StarButton.jsx`

Props: `isStarred: boolean`, `onToggle: () => void`, `loading: boolean`

A simple star icon (filled = starred, outline = not). Clicking calls `onToggle`. Shows a spinner while the API call is in-flight.

---

### 5.5 API Client Layer (`src/api/client.js`)

All fetch calls live in one file. This means if you change the backend URL or add auth headers later, you change it in one place.

```javascript
const BASE = "http://localhost:8000/api"

export const uploadQuiz = (file) => { ... }
export const getQuizzes = () => { ... }
export const getQuiz = (quizId) => { ... }
export const deleteQuiz = (quizId) => { ... }

export const submitAttempt = (quizId, answers) => { ... }
export const getAttempts = (quizId) => { ... }
export const getAttempt = (quizId, attemptId) => { ... }

export const starQuestion = (quizId, questionIndex) => { ... }
export const unstarQuestion = (quizId, questionIndex) => { ... }
export const getStarred = () => { ... }

export const getWrongAnswers = () => { ... }
export const clearWrongAnswers = () => { ... }
```

---

### 5.6 State Management

No Redux, no Zustand. State is kept local to each page using `useState` and `useEffect`. Data is fetched fresh on each page mount. This is fine for personal use — you won't notice the few milliseconds of loading.

The one exception: the `answers` state during a live quiz is component-level state in `Quiz.jsx`. If you navigate away mid-quiz and come back, answers are lost. This is acceptable — you just restart the quiz.

---

## 6. Feature Specifications

### 6.1 Upload & Parse

- Only `.md` files accepted (frontend validates MIME type + extension before uploading)
- File size: no limit enforced (all your quiz files will be tiny)
- Duplicate filename: allowed — each upload gets a new UUID-based `quiz_id`
- Parse errors: backend returns `{ error: "Question 3 is missing **Answer:** line" }` and the frontend shows it clearly
- On successful upload: quiz is immediately available in the dashboard

### 6.2 Quiz Flow (Question-by-Question)

- One question displayed at a time
- No time limit
- Can go back to previous questions and change answer anytime before submit
- Progress is shown in the progress bar
- Cannot skip to an unanswered question intentionally (but can use prev/next to pass it)
- Submit is available at any point (with a count of unanswered questions shown)
- After submit: cannot change answers (results are locked)

### 6.3 Code Rendering

- Code blocks in questions are rendered with full syntax highlighting
- Supported languages: everything that `react-syntax-highlighter` + Prism supports (Python, Java, C++, SQL, JavaScript, C, Bash, etc.)
- Language is auto-detected from the fenced code block language tag in the MD file (` ```python `)
- If no language tag is given, the code block renders as plain monospace text
- Long lines scroll horizontally instead of wrapping
- Copy-to-clipboard button on every code block

### 6.4 Scoring & Attempts History

- Score is calculated on the backend (not the frontend) to keep it consistent
- Every attempt is saved with: timestamp, all answers, score, wrong indices
- Dashboard shows best score and last attempt date for each quiz
- You can click any past attempt to review the full breakdown
- No attempt limit — retake as many times as you want
- Attempts are never automatically deleted

### 6.5 Starred Questions

- You can star any question during a quiz or from the results page
- Stars persist across sessions (stored in `data/starred.json` on backend)
- The Starred page shows all starred questions grouped by quiz with full question content
- Unstarring is immediate and reflected in all views
- A question can be starred from multiple places (quiz view, results view, starred page) — it won't duplicate

### 6.6 Wrong Answers Tracker

- Wrong answers are recorded automatically every time you submit an attempt
- If you answer the same question wrong in three different attempts, it appears three times in the wrong answers list (with different attempt dates)
- Wrong answers page is sortable by quiz and filterable by date
- "Clear all" button wipes the entire `wrong.json` file (with a confirmation dialog)
- Wrong answers show: question text, code (if any), your answer, correct answer, quiz name, attempt date

### 6.7 Persistence Across Restarts

- All data is on disk in `backend/data/`
- The `data/` folder is never deleted by the app itself
- If you move the project to a new machine, just copy the `data/` folder and all your history comes with it
- On startup, `storage.py` checks if the `data/` directories and files exist; if not, it creates them with empty defaults
- No migration needed — the schema is flat JSON with forward-compatible structure

---

## 7. Data Schemas (JSON)

### Quiz object (stored in `data/quizzes/{id}.json`)

```
{
  id: string,                     // UUID-based short ID
  title: string,                  // from first # heading in MD
  subject: string | null,         // optional, parsed from filename or first heading
  filename: string,               // original uploaded filename
  uploaded_at: ISO8601 string,
  question_count: integer,
  questions: [
    {
      index: integer,             // 0-based
      text: string,               // plain question text (no code block)
      code: string | null,        // code content if present
      code_language: string | null,
      options: {
        A: string,
        B: string,
        C: string,
        D: string
      },
      correct_answer: string      // one of "A", "B", "C", "D"
    }
  ]
}
```

### Attempt object (inside `data/attempts/{quiz_id}.json`)

```
{
  attempt_id: string,             // "atmp_{timestamp}"
  attempted_at: ISO8601 string,
  score: integer,
  total: integer,
  percentage: float,
  answers: {                      // user's submitted answers
    "0": "B",
    "1": "C",
    ...
  },
  wrong_indices: integer[]        // 0-based question indices answered wrong
}
```

### Starred entry (inside `data/starred.json`)

```
{
  quiz_id: string,
  question_index: integer,
  starred_at: ISO8601 string
}
```

### Wrong answer entry (inside `data/wrong.json`)

```
{
  quiz_id: string,
  quiz_title: string,
  question_index: integer,
  question_text: string,
  your_answer: string,
  correct_answer: string,
  attempt_id: string,
  attempted_at: ISO8601 string
}
```

---

## 8. Dependencies

### Backend (`requirements.txt`)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9      # for file upload parsing
```

That's it. The MD parser is pure Python with no external dependencies.

### Frontend (`package.json` dependencies)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "react-markdown": "^9.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.2.0"
  }
}
```

---

## 9. Environment & Running Locally

### First-time setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Access

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Docs (auto-generated by FastAPI): `http://localhost:8000/docs`

### Access from phone (same WiFi)

1. Find your laptop's local IP: `ipconfig` (Windows) or `ifconfig` / `ip addr` (Linux/Mac)
2. Start backend with: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. Update `frontend/src/api/client.js` `BASE` URL to `http://192.168.x.x:8000/api`
4. Start frontend with: `npm run dev -- --host`
5. Access from phone: `http://192.168.x.x:5173`

---

## 10. Folder Structure (Full)

```
quiz-app/
│
├── build-plan.md                   ← This file
├── implementation-plan.md          ← Phase-by-phase build guide
├── README.md                       ← Quick start instructions
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── quizzes.py
│   │   ├── attempts.py
│   │   └── bookmarks.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── md_parser.py
│   │   └── storage.py
│   │
│   └── data/                       ← gitignore this folder
│       ├── quizzes/
│       ├── attempts/
│       ├── starred.json
│       └── wrong.json
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    │
    └── src/
        ├── main.jsx
        ├── App.jsx
        │
        ├── api/
        │   └── client.js
        │
        ├── pages/
        │   ├── Home.jsx
        │   ├── Dashboard.jsx
        │   ├── Quiz.jsx
        │   ├── Results.jsx
        │   ├── Starred.jsx
        │   └── WrongAnswers.jsx
        │
        └── components/
            ├── Navbar.jsx
            ├── QuestionCard.jsx
            ├── MarkdownRenderer.jsx
            ├── CodeBlock.jsx
            ├── ProgressBar.jsx
            ├── StarButton.jsx
            ├── AttemptHistoryCard.jsx
            └── ScoreBadge.jsx
```

---

## 11. Edge Cases & Constraints

| Scenario | Behaviour |
|---|---|
| MD file has no `**Answer:**` on a question | Backend returns 400 with message `"Question N is missing an Answer line"` |
| MD file has only 1 question | Valid. Works fine. |
| User submits quiz with some unanswered questions | Allowed. Unanswered questions are scored as wrong. A warning is shown before submit. |
| Same MD file uploaded twice | Creates two separate quizzes with different IDs. No deduplication. |
| `data/` folder is deleted manually | On next backend startup, all folders and empty JSON files are re-created. All quiz/attempt data is gone permanently. |
| Very long question text | Question card scrolls vertically. No truncation. |
| Code block with no language tag | Renders as plain monospace. No syntax highlighting. |
| Navigating away from an in-progress quiz | Answers are lost (no mid-quiz save). User must start over. |
| Star the same question twice | Backend deduplicates — checks if entry already exists before inserting. |
| Network error during submit | Frontend shows an error toast. Attempt is NOT saved. User can try again. |

---

## 12. Future Enhancements (Optional)

These are not in scope for the initial build but are easy to add later given the architecture:

- **Timer per question or timer per quiz**: Add `started_at` timestamp to the attempt and compute elapsed time.
- **Shuffle questions**: A checkbox on the quiz start screen to randomize question order. The mapping back to original indices is maintained for scoring.
- **Shuffle options**: Randomize A/B/C/D order each time. Requires remapping the correct answer letter.
- **Export wrong answers as MD**: A button that generates a new `.md` file from your wrong answers for focused re-practice.
- **PWA support**: Add `manifest.json` and a service worker. The app becomes installable on mobile as a home screen icon.
- **Dark mode**: A toggle in the navbar. CSS variables make this easy to add.
- **Subject tagging**: Parse a subject tag from the MD filename (`dbms_normalisation.md` → subject: `DBMS`) and filter the dashboard by subject.
- **Search**: A search box on the dashboard to find questions by keyword.
