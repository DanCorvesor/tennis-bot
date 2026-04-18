import time
from datetime import datetime, timedelta
from typing import Callable

from bot.basket import BasketManager, SlotUnavailableError
from bot.notifier import Notifier, SlotFound
from bot.scanner import CourtScanner, Slot


class Scheduler:
    """Orchestrates the polling lifecycle around the 8pm slot release."""

    def __init__(
        self,
        scanner: CourtScanner,
        basket: BasketManager,
        notifier: Notifier,
        *,
        now: Callable[[], datetime] = datetime.now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._scanner = scanner
        self._basket = basket
        self._notifier = notifier
        self._now = now
        self._sleep = sleep

    def run(self) -> int:
        raise NotImplementedError


def poll_interval_seconds(now: datetime, release_at: datetime) -> float:
    """Returns the appropriate sleep interval for the current position in the polling window."""
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
