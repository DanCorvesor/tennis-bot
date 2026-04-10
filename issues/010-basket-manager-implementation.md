## Parent PRD

`issues/prd.md`

## What to build

Implement the Basket Manager so all tests from `issues/009` pass, then manually validate the full add-to-basket flow on the live ClubSpark site. The module navigates to the slot booking page, clicks through to add to basket, and returns the basket checkout URL for inclusion in the WhatsApp notification.

## Acceptance criteria

- [ ] All tests in `tests/test_basket.py` pass
- [ ] Bot successfully navigates to a slot's booking URL and adds it to the ClubSpark basket
- [ ] Returns a valid basket checkout URL (e.g. `https://clubspark.lta.org.uk/...basket...`)
- [ ] Raises a descriptive exception if the slot is no longer available at time of basket add
- [ ] Manually verified: bot adds a real slot to basket and the basket URL is accessible when opened in a browser while logged in

## Blocked by

- Blocked by `issues/009-basket-manager-tests-stubs.md`

## User stories addressed

- User story 8, 10
