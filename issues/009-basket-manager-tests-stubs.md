## Parent PRD

`issues/prd.md`

## What to build

Write tests and the interface stub for the Basket Manager module. The Basket Manager takes a slot's booking URL, navigates to it in the authenticated browser session, adds it to the ClubSpark basket, and returns the basket checkout URL. Tests mock the Playwright interactions — live validation is manual in `issues/010`.

## Acceptance criteria

- [ ] `bot/basket.py` exists and exports the expected interface (stub only)
- [ ] `tests/test_basket.py` exists with tests covering:
  - [ ] Given a valid booking URL, returns a basket checkout URL
  - [ ] If adding to basket fails (e.g. slot no longer available), raises a descriptive exception
  - [ ] The returned URL points to the ClubSpark basket/checkout path
  - [ ] Playwright page interactions are mocked — no real browser launched during tests
- [ ] `pytest` runs without import errors; basket tests fail expectedly against the stub

## Blocked by

- Blocked by `issues/008-court-scanner-implementation.md`

## User stories addressed

- User story 8, 10
