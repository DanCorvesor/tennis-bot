## Parent PRD

`issues/prd.md`

## What to build

Write integration tests and the stub entry point for the Scheduler. The Scheduler is the main script invoked by cron — it orchestrates the polling loop, ramps up frequency as 8pm approaches, drives the Scanner and Basket Manager, and dispatches the correct Notifier message. Tests mock Scanner, Basket Manager, and Notifier to assert on the Scheduler's orchestration logic only.

## Acceptance criteria

- [ ] `bot/scheduler.py` exists and exports the expected interface (stub only)
- [ ] `tests/test_scheduler.py` exists with tests covering:
  - [ ] When scanner finds a slot: Basket Manager is called, then Notifier sends "slot found" with basket URL
  - [ ] When scanner returns `None` after the full retry window: Notifier sends "nothing available"
  - [ ] When any module raises an exception: Notifier sends "error" with the exception description
  - [ ] Polling retries for up to 5 minutes after 8pm at 10-second intervals before giving up
  - [ ] Scanner and Basket Manager are mocked — no real browser or network calls during tests
  - [ ] Notifier is mocked — no real WhatsApp messages sent during tests
- [ ] `pytest` runs without import errors; scheduler tests fail expectedly against the stub

## Blocked by

- Blocked by `issues/004-notifier-implementation.md`
- Blocked by `issues/010-basket-manager-implementation.md`

## User stories addressed

- User story 1, 12, 13, 14
