from unittest.mock import MagicMock

import pytest

from bot.basket import BasketManager, SlotUnavailableError


BOOKING_URL = "https://clubspark.lta.org.uk/SouthwarkPark/Booking/Book?id=abc123"
BASKET_URL = "https://clubspark.lta.org.uk/basket/cs-basket-42"


def _fake_page(*, basket_url: str | None = BASKET_URL, slot_unavailable: bool = False):
    page = MagicMock(name="page")

    confirm_button = MagicMock(name="confirm_button")
    confirm_button.count.return_value = 0 if slot_unavailable else 1

    unavailable_banner = MagicMock(name="unavailable_banner")
    unavailable_banner.count.return_value = 1 if slot_unavailable else 0

    def locator(selector: str):
        if "Confirm" in selector or "Add to basket" in selector or "basket-btn" in selector:
            return confirm_button
        if "unavailable" in selector.lower() or "error" in selector.lower():
            return unavailable_banner
        return MagicMock(count=MagicMock(return_value=0))

    page.locator.side_effect = locator
    page.get_by_role.side_effect = lambda role, name=None: confirm_button

    page.url = basket_url if basket_url else ""
    return page


def test_returns_basket_checkout_url_on_success():
    page = _fake_page()
    basket = BasketManager(page)

    url = basket.add_to_basket(BOOKING_URL)

    assert url == BASKET_URL
    page.goto.assert_any_call(BOOKING_URL)


def test_raises_when_slot_no_longer_available():
    page = _fake_page(slot_unavailable=True)
    basket = BasketManager(page)

    with pytest.raises(SlotUnavailableError):
        basket.add_to_basket(BOOKING_URL)


def test_returned_url_points_to_basket_path():
    page = _fake_page(basket_url="https://clubspark.lta.org.uk/basket/cs-basket-42")
    basket = BasketManager(page)

    url = basket.add_to_basket(BOOKING_URL)

    assert "basket" in url
    assert url.startswith("https://clubspark.lta.org.uk")


def test_no_real_browser_launched():
    # Pure mock — nothing here would reach the network.
    page = _fake_page()
    BasketManager(page).add_to_basket(BOOKING_URL)
    assert page.goto.called
