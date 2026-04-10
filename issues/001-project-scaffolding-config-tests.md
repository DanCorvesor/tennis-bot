## Parent PRD

`issues/prd.md`

## What to build

Set up the project skeleton and write tests for the Config Loader module before any implementation exists. This slice establishes the project structure, dependency management, test framework, and the test suite that defines the expected behaviour of config loading — including validation of required fields and correct parsing of all `.env` values.

The end result is a repo that can run `pytest` (all tests fail with `NotImplementedError` or missing imports), a clear module interface for `config.py`, and a passing test run once 002 is merged.

## Acceptance criteria

- [ ] `pyproject.toml` or `requirements.txt` exists with all dependencies pinned (playwright, twilio, python-dotenv, pytest)
- [ ] Project directory structure is in place: `bot/`, `tests/`, `issues/`
- [ ] A `.env.example` file documents all required and optional variables (no real credentials)
- [ ] `tests/test_config.py` exists with tests covering:
  - [ ] All required fields load correctly from a valid `.env`
  - [ ] Missing required fields raise a clear, descriptive error
  - [ ] `PREFERRED_TIMES` parses to an ordered list
  - [ ] `COURTS` parses to a list of URLs
  - [ ] `WHATSAPP_ALLOWLIST` parses to a list of phone number strings
  - [ ] `SLOT_DURATION_HOURS` parses to an integer
- [ ] `bot/config.py` exports the expected interface (stub only — functions raise `NotImplementedError`)
- [ ] `pytest` runs without import errors; config tests fail expectedly against the stub

## Blocked by

None — can start immediately.

## User stories addressed

- User story 16
