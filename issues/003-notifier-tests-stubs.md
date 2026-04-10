## Parent PRD

`issues/prd.md`

## What to build

Write the test suite and interface stub for the Notifier module. The Notifier is responsible for sending WhatsApp messages via Twilio for three scenarios: slot found (with basket URL), nothing available, and bot error. Tests use a mocked Twilio client — no real messages are sent.

## Acceptance criteria

- [ ] `bot/notifier.py` exists and exports the expected interface (stub only)
- [ ] `tests/test_notifier.py` exists with tests covering:
  - [ ] "Slot found" message is sent to every number in the allowlist with the correct court name, day, time, and basket URL
  - [ ] "Nothing available" message is sent to every number in the allowlist
  - [ ] "Error" message is sent to every number in the allowlist and includes the error description
  - [ ] Each message is sent as a separate Twilio API call per recipient
  - [ ] Twilio client is mocked — no real API calls made during tests
- [ ] `pytest` runs without import errors; notifier tests fail expectedly against the stub

## Blocked by

- Blocked by `issues/002-config-loader-implementation.md`

## User stories addressed

- User story 9, 10, 11, 13, 14, 15
