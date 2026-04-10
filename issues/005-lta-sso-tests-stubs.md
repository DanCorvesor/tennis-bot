## Parent PRD

`issues/prd.md`

## What to build

Write tests and the interface stub for the Session Manager module. Because the Session Manager drives a real browser through LTA's OAuth flow, automated tests focus on the interface contract and the re-authentication logic — not the live HTML interactions, which are validated manually in `issues/006`.

Tests should mock the Playwright browser context and assert on the decisions the Session Manager makes (e.g. detect expired session → trigger re-auth, persist cookies after login).

## Acceptance criteria

- [ ] `bot/session.py` exists and exports the expected interface (stub only)
- [ ] `tests/test_session.py` exists with tests covering:
  - [ ] On first run (no saved cookies), the login flow is triggered
  - [ ] On subsequent runs with valid saved cookies, login flow is skipped
  - [ ] If the session is detected as expired (e.g. redirected to login page mid-run), re-authentication is triggered exactly once before raising
  - [ ] Cookie file path is derived from config
  - [ ] Playwright browser context is mocked — no real browser launched during tests
- [ ] `pytest` runs without import errors; session tests fail expectedly against the stub

## Blocked by

- Blocked by `issues/002-config-loader-implementation.md`

## User stories addressed

- User story 6, 7
