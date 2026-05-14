import re


def parse_quiz(raw_text: str, filename: str) -> dict:
    """
    Parse raw Markdown text into a structured quiz dict.

    Returns:
        {
            "title": str,
            "filename": str,
            "question_count": int,
            "questions": [...]
        }

    Raises:
        ValueError: with a human-readable message if parsing fails.
    """
    # Normalise line endings
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # --- Quiz title ---
    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = re.sub(r"\.md$", "", filename, flags=re.IGNORECASE)

    # --- Split into question blocks ---
    # Split on every occurrence of \n## Q followed by digits (and anything after)
    blocks = re.split(r"\n## Q\d+[^\n]*\n", text)
    # blocks[0] is the file header — discard it
    question_blocks = blocks[1:]

    if not question_blocks:
        raise ValueError("No questions found. Make sure questions start with '## Q1', '## Q2', etc.")

    questions = []
    for idx, block in enumerate(question_blocks):
        question = _parse_question(block, idx)
        questions.append(question)

    return {
        "title": title,
        "filename": filename,
        "question_count": len(questions),
        "questions": questions,
    }


# Regex for a fenced code block: ```optional_lang\n...content...\n```
_CODE_BLOCK_RE = re.compile(
    r"```([^\n`]*)\n(.*?)```",
    re.DOTALL,
)

# Regex for option lines: A) text  or  A) text ✓
_OPTION_RE = re.compile(r"^([A-D])\)\s+(.+)$", re.MULTILINE)

# Regex for the answer declaration
_ANSWER_RE = re.compile(r"\*\*Answer:\s*([A-D])\*\*", re.IGNORECASE)


def _parse_question(block: str, index: int) -> dict:
    """Parse a single question block (text after the ## Qn header line)."""
    n = index + 1  # 1-based for error messages

    # --- Extract code block ---
    code = None
    code_language = None
    code_match = _CODE_BLOCK_RE.search(block)
    if code_match:
        code_language = code_match.group(1).strip() or None
        code = code_match.group(2)
        # Remove the code block from the block so it doesn't pollute text
        block = block[:code_match.start()] + block[code_match.end():]

    # --- Extract correct answer ---
    answer_match = _ANSWER_RE.search(block)
    if not answer_match:
        raise ValueError(
            f"Question {n} is missing the **Answer:** line. "
            "Add '**Answer: X**' (where X is A, B, C or D) to every question."
        )
    correct_answer = answer_match.group(1).upper()
    if correct_answer not in ("A", "B", "C", "D"):
        raise ValueError(
            f"Question {n} has an invalid answer letter: '{correct_answer}'. Must be A, B, C or D."
        )

    # --- Extract options ---
    option_matches = _OPTION_RE.findall(block)
    options: dict[str, str] = {}
    for letter, text in option_matches:
        # Strip the ✓ marker and surrounding whitespace
        clean_text = text.rstrip().rstrip("✓").rstrip()
        options[letter] = clean_text

    for letter in ("A", "B", "C", "D"):
        if letter not in options:
            raise ValueError(
                f"Question {n} is missing option {letter}. "
                "All four options (A, B, C, D) are required."
            )

    # --- Extract question text ---
    # Everything before the first option line (A) ...) is the question body
    first_option_match = re.search(r"^[A-D]\)\s+", block, re.MULTILINE)
    if first_option_match:
        question_body = block[: first_option_match.start()]
    else:
        question_body = block

    # Remove the **Answer:** line from the body as well
    question_body = _ANSWER_RE.sub("", question_body)

    # Strip horizontal rules and extra whitespace
    question_body = re.sub(r"^---+\s*$", "", question_body, flags=re.MULTILINE)
    question_text = question_body.strip()

    if not question_text:
        raise ValueError(
            f"Question {n} has no question text. "
            "Add the question body between the '## Qn' header and the options."
        )

    return {
        "index": index,
        "text": question_text,
        "code": code,
        "code_language": code_language,
        "options": options,
        "correct_answer": correct_answer,
    }
