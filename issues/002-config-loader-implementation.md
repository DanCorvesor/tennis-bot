## Parent PRD

`issues/prd.md`

## What to build

Implement the Config Loader module so that all tests from `issues/001` pass. The module reads from `.env`, validates required fields, and returns a typed configuration object consumed by all other modules.

## Acceptance criteria

- [ ] `bot/config.py` fully implemented — no `NotImplementedError` stubs remain
- [ ] All tests in `tests/test_config.py` pass
- [ ] Config object exposes typed fields for: LTA credentials, Twilio credentials, court URLs, preferred times (ordered list), booking days, slot duration, WhatsApp sender, recipient, and allowlist
- [ ] A missing required field raises an exception with a human-readable message naming the missing variable
- [ ] Card fallback fields (`CARD_NUMBER`, `CARD_EXPIRY`, `CARD_CVV`, `CARD_NAME`) are optional and default to `None`

## Blocked by

- Blocked by `issues/001-project-scaffolding-config-tests.md`

## User stories addressed

- User story 16
