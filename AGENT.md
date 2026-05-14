# Agent Operating Rules

## Task Execution

- Always use `manage_todo_list` for every multi-step request.
- Mark a todo as **in-progress** before starting it; mark **completed** immediately after finishing.
- Never skip tasks silently.
- Work step-by-step — complete each todo before moving to the next.

## Post-Task Clarification

After completing tasks, surface any ambiguities or edge cases.

Example: "Completed X, Y, Z. Before moving on — should I also do…?"

## Post-Task Completion Prompt

The **last item** in every todo list must be **"Ask user for next steps"**.

After completing all other todos, the agent MUST call `vscode_askQuestions` with:

- A concise header
- Clickable option buttons for each natural next action
- A freeform input field so the user can type a custom request
- Never replace `vscode_askQuestions` with a plain text prompt

## Interaction Rules

- Prefer `vscode_askQuestions` over open-ended plain text whenever presenting choices.
- Every question set must include at least 3 concrete options plus freeform input.
- Never end a session with "Let me know if you need anything" — always present specific options.
