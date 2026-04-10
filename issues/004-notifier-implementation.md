## Parent PRD

`issues/prd.md`

## What to build

Implement the Notifier module so all tests from `issues/003` pass. Integrate the Twilio Python SDK to send WhatsApp messages to all numbers in the allowlist for each of the three message types.

## Acceptance criteria

- [ ] All tests in `tests/test_notifier.py` pass
- [ ] "Slot found" message includes: court name, day, time, and a direct ClubSpark basket URL
- [ ] "Nothing available" message clearly states no slots were found this week
- [ ] "Error" message includes a description of what went wrong
- [ ] All recipients in the allowlist receive each message (one Twilio API call per recipient)
- [ ] Twilio `from` number is read from config (`TWILIO_WHATSAPP_FROM`)
- [ ] Manually verified: a real "slot found" test message is received on +447512211264 via WhatsApp (requires real Twilio credentials in `.env`)

## Blocked by

- Blocked by `issues/003-notifier-tests-stubs.md`

## User stories addressed

- User story 9, 10, 11, 13, 14, 15
