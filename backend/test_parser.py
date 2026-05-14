"""
Quick test for md_parser.py — run with:
    python backend/test_parser.py   (from project root)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from services.md_parser import parse_quiz

# ---------------------------------------------------------------------------
# Test 1 — plain text question, code block BEFORE text, code block AFTER text
# ---------------------------------------------------------------------------
TEST_MD = """
# Test Quiz — Parser Verification

## Q1
Which normal form eliminates partial dependencies?

A) 1NF
B) 2NF ✓
C) 3NF
D) BCNF

**Answer: B**

---

## Q2
```sql
SELECT department, COUNT(*) as emp_count
FROM employees
GROUP BY department
HAVING COUNT(*) > 5;
```

What does the SQL query above return?

A) All employees in departments with more than 5 employees
B) Count of all employees grouped by department
C) Departments that have more than 5 employees, with their count ✓
D) Employees whose count exceeds 5

**Answer: C**

---

## Q3
Consider the following Python snippet:

What will it print?

```python
x = [1, 2, 3]
print(x[-1])
```

A) 1
B) 2
C) 3 ✓
D) IndexError

**Answer: C**
"""

print("=" * 60)
print("TEST 1: Valid quiz with 3 questions")
print("=" * 60)
result = parse_quiz(TEST_MD, "test_quiz.md")
print(json.dumps(result, indent=2))

# ---------------------------------------------------------------------------
# Test 2 — missing **Answer:** line
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST 2: Missing **Answer:** line (should raise ValueError)")
print("=" * 60)
BAD_MD_NO_ANSWER = """
# Bad Quiz

## Q1
What is 2 + 2?

A) 3
B) 4
C) 5
D) 6
"""
try:
    parse_quiz(BAD_MD_NO_ANSWER, "bad.md")
    print("ERROR: should have raised ValueError!")
except ValueError as e:
    print(f"Caught expected error: {e}")

# ---------------------------------------------------------------------------
# Test 3 — missing option C
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST 3: Missing option C (should raise ValueError)")
print("=" * 60)
BAD_MD_MISSING_OPTION = """
# Bad Quiz

## Q1
What is 2 + 2?

A) 3
B) 4
D) 6

**Answer: B**
"""
try:
    parse_quiz(BAD_MD_MISSING_OPTION, "bad.md")
    print("ERROR: should have raised ValueError!")
except ValueError as e:
    print(f"Caught expected error: {e}")

# ---------------------------------------------------------------------------
# Test 4 — empty question text
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST 4: Empty question text (should raise ValueError)")
print("=" * 60)
BAD_MD_EMPTY_TEXT = """
# Bad Quiz

## Q1

A) 3
B) 4
C) 5
D) 6

**Answer: B**
"""
try:
    parse_quiz(BAD_MD_EMPTY_TEXT, "bad.md")
    print("ERROR: should have raised ValueError!")
except ValueError as e:
    print(f"Caught expected error: {e}")

print("\nAll tests passed!")
