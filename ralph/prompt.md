# Ralph — Autonomous Issue Worker

You are implementing a single issue from a tennis court booking bot project. Read the issue file carefully and follow it precisely.

## Rules

1. Read the issue's **acceptance criteria** — every checkbox must be satisfied.
2. Read the **parent PRD** (`issues/prd.md`) for full project context.
3. Read any **blocker issues** referenced in "Blocked by" to understand what code already exists.
4. Write clean, minimal Python. No unnecessary abstractions.
5. If the issue is a **test + stub issue** (ends with "tests" or "stubs"):
   - Write the test file in `tests/`
   - Write the stub module in `bot/` with the interface defined but raising `NotImplementedError`
   - Ensure `pytest` collects all tests without import errors
6. If the issue is an **implementation issue**:
   - Make all existing tests pass
   - Do not modify the tests unless they have a genuine bug
7. Commit all changes with a descriptive message.
8. When you are done, output: `<promise>DONE</promise>`
9. If there are no more issues to work on, output: `<promise>NO MORE TASKS</promise>`
