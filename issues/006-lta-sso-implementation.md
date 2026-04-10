## Parent PRD

`issues/prd.md`

## What to build

Implement the Session Manager so all tests from `issues/005` pass, then manually validate the full LTA OAuth flow against the live ClubSpark site. The module handles: launching a headless Playwright browser, performing the LTA SSO redirect login, persisting cookies to disk, and reusing the session on subsequent runs.

## Acceptance criteria

- [ ] All tests in `tests/test_session.py` pass
- [ ] Full LTA OAuth login flow works end-to-end in headless Playwright (LTA login page → credentials entered → redirect back to ClubSpark → authenticated)
- [ ] Browser cookies are saved to disk after successful login
- [ ] On next run, saved cookies are loaded and login is skipped if session is still valid
- [ ] If session is expired mid-run, the module re-authenticates once and continues
- [ ] Manually verified: bot successfully reaches an authenticated ClubSpark page without human interaction

## Blocked by

- Blocked by `issues/005-lta-sso-tests-stubs.md`

## User stories addressed

- User story 6, 7
