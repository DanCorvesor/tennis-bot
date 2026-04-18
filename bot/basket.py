class SlotUnavailableError(RuntimeError):
    """Raised when a slot is no longer bookable by the time we try to add it to basket."""


class BasketManager:
    def __init__(self, page) -> None:
        self._page = page

    def add_to_basket(self, booking_url: str) -> str:
        page = self._page
        page.goto(booking_url)

        if page.locator(".booking-unavailable, .error-message").count() > 0:
            raise SlotUnavailableError(
                f"Slot at {booking_url} is no longer available."
            )

        confirm = page.locator(
            'button.basket-btn, button:has-text("Add to basket"), button:has-text("Confirm")'
        )
        if confirm.count() == 0:
            raise SlotUnavailableError(
                f"No basket / confirm button on {booking_url}; slot likely gone."
            )
        confirm.first.click()
        page.wait_for_url("**/basket/**", timeout=15_000)
        return page.url
