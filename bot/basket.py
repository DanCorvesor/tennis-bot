class SlotUnavailableError(RuntimeError):
    """Raised when a slot is no longer bookable by the time we try to add it to basket."""


class BasketManager:
    def __init__(self, page) -> None:
        self._page = page

    def add_to_basket(self, booking_url: str) -> str:
        """Navigate to booking_url, add the slot to the ClubSpark basket,
        and return the basket checkout URL."""
        raise NotImplementedError
