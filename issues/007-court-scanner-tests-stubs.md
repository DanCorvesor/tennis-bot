## Parent PRD

`issues/prd.md`

## What to build

Write tests and the interface stub for the Court Scanner module. The scanner is given an authenticated session and a priority-ordered list of (day, time) tuples, polls the three ClubSpark court pages, and returns the first available matching slot. Tests mock the page responses — no real browser required.

## Acceptance criteria

- [ ] `bot/scanner.py` exists and exports the expected interface (stub only)
- [ ] `tests/test_scanner.py` exists with tests covering:
  - [ ] Returns the highest-priority available slot when multiple options exist (Sat 10am beats Sun 10am beats Sat 11am, etc.)
  - [ ] Skips unavailable slots and falls through to the next priority
  - [ ] Returns `None` when no slots are available across all courts and all times
  - [ ] Checks all three court URLs for each priority level before moving to the next
  - [ ] Mocked page HTML drives availability — no live HTTP calls during tests
- [ ] `pytest` runs without import errors; scanner tests fail expectedly against the stub

## Blocked by

- Blocked by `issues/006-lta-sso-implementation.md`

## User stories addressed

- User story 2, 3, 4, 5
