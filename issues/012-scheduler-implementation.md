## Parent PRD

`issues/prd.md`

## What to build

Implement the Scheduler so all tests from `issues/011` pass. This is the main entry point invoked by cron. It manages the full polling lifecycle: starting at 7:58pm, ramping frequency as 8pm approaches, retrying for 5 minutes after release, then dispatching the appropriate notification.

## Acceptance criteria

- [ ] All tests in `tests/test_scheduler.py` pass
- [ ] Polling starts at 7:58pm at 5-second intervals
- [ ] Polling ramps to 1-second intervals from 7:59:30pm
- [ ] After 8:00pm, retries at 10-second intervals for up to 5 minutes
- [ ] On slot found: adds to basket, sends "slot found" WhatsApp with basket URL, exits
- [ ] On 5-minute timeout with nothing found: sends "nothing available" WhatsApp, exits
- [ ] On any unhandled exception: sends "error" WhatsApp with description, exits with non-zero code
- [ ] Script is executable as `python -m bot.scheduler` with no arguments (reads all config from `.env`)
- [ ] Manually verified: full end-to-end run on local machine reaches the notification stage correctly

## Blocked by

- Blocked by `issues/011-scheduler-integration-tests.md`

## User stories addressed

- User story 1, 12, 13, 14
