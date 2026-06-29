from unittest.mock import MagicMock

import pytest

from bot.basket import BasketManager, SlotUnavailableError


SLOT_ID = "booking-ad7d3c7b-9dff-4442-bb18-4761970f11c0|2026-05-19|600"
CHECKOUT_URL = "https://clubspark.lta.org.uk/SouthwarkPark/Booking/Book?ResourceID=abc"


def _fake_page(*, checkout_url: str = CHECKOUT_URL, slot_gone: bool = False):
    page = MagicMock(name="page")

    slot_link = MagicMock(name="slot_link")
    slot_link.count.return_value = 0 if slot_gone else 1

    continue_btn = MagicMock(name="continue_btn")
    confirm_btn = MagicMock(name="confirm_btn")

    page.locator.return_value = slot_link
    page.get_by_role.side_effect = lambda role, name=None: (
        continue_btn if name == "Continue booking" else confirm_btn
    )
    page.url = checkout_url
    return page


def test_returns_checkout_url_on_success():
    page = _fake_page()
    basket = BasketManager(page)

    url = basket.add_to_basket(SLOT_ID)

    assert url == CHECKOUT_URL
    page.locator.assert_any_call(f'a[data-test-id="{SLOT_ID}"]')
    page.locator.assert_any_call("#booking-duration")


def test_raises_when_slot_no_longer_available():
    page = _fake_page(slot_gone=True)
    basket = BasketManager(page)

    with pytest.raises(SlotUnavailableError):
        basket.add_to_basket(SLOT_ID)


def test_clicks_continue_then_waits_for_confirm():
    page = _fake_page()
    basket = BasketManager(page)

    basket.add_to_basket(SLOT_ID)

    page.get_by_role.assert_any_call("button", name="Continue booking")
    page.get_by_role.assert_any_call("button", name="Confirm and pay")


def test_no_real_browser_launched():
    page = _fake_page()
    BasketManager(page).add_to_basket(SLOT_ID)
    assert page.locator.called
