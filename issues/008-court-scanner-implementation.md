## Parent PRD

`issues/prd.md`

## What to build

Implement the Court Scanner so all tests from `issues/007` pass, then manually validate against the live ClubSpark availability pages. The scanner navigates each court's booking page, parses available time slots, and returns the best match according to the priority order defined in config.

## Acceptance criteria

- [ ] All tests in `tests/test_scanner.py` pass
- [ ] Scanner correctly parses the ClubSpark availability page for each of the three courts
- [ ] Priority order respected: Sat 10am > Sun 10am > Sat 11am > Sun 11am > Sat 9am > Sun 9am
- [ ] Returns a result object containing: court name, court URL, day, time, and booking URL for the slot
- [ ] Returns `None` cleanly when nothing is available
- [ ] Manually verified: scanner correctly identifies available and unavailable slots on the live site

## Blocked by

- Blocked by `issues/007-court-scanner-tests-stubs.md`

## User stories addressed

- User story 2, 3, 4, 5
