class SlotUnavailableError(RuntimeError):
    """Raised when a slot is no longer bookable by the time we try to add it to basket."""


class BasketManager:
    def __init__(self, page, duration_minutes: int = 60) -> None:
        self._page = page
        self._duration_minutes = duration_minutes

    def add_to_basket(self, slot_id: str) -> str:
        page = self._page

        slot_link = page.locator(f'a[data-test-id="{slot_id}"]')
        slot_link.wait_for(timeout=10_000)
        if slot_link.count() == 0:
            raise SlotUnavailableError(
                f"Slot {slot_id} is no longer available."
            )

        slot_link.scroll_into_view_if_needed()
        slot_link.click()

        start_minutes = int(slot_id.rsplit("|", 1)[-1])
        end_minutes = str(start_minutes + self._duration_minutes)
        page.locator("#booking-duration").select_option(value=end_minutes)

        page.get_by_role("button", name="Continue booking").click()
        page.get_by_role("button", name="Confirm and pay").wait_for(timeout=15_000)
        return page.url
