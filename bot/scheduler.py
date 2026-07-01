import time
import traceback
from datetime import datetime, timedelta
from typing import Callable

from bot.basket import BasketManager
from bot.config import load_config
from bot.notifier import Notifier, NtfyNotifier, SlotFound
from bot.scanner import CourtScanner, Slot, build_priorities, make_playwright_probe
from bot.session import (
    SessionManager,
    clubspark_login,
    playwright_browser_factory,
)


RETRY_WINDOW = timedelta(minutes=5)


class Scheduler:
    """Orchestrates the polling lifecycle around the 8pm slot release."""

    def __init__(
        self,
        scanner: CourtScanner,
        basket: BasketManager,
        notifier: Notifier,
        *,
        duration_hours: int = 1,
        release_hour: int = 20,
        now: Callable[[], datetime] = datetime.now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._scanner = scanner
        self._basket = basket
        self._notifier = notifier
        self._duration_hours = duration_hours
        self._release_hour = release_hour
        self._now = now
        self._sleep = sleep

    def run(self) -> int:
        try:
            slot = self._poll_until_found_or_timeout()
            if slot is None:
                self._notifier.send_nothing_available()
                return 0

            basket_url = self._basket.add_to_basket(slot.booking_url)
            self._notifier.send_slot_found(
                SlotFound(
                    court_name=slot.court_name,
                    day=slot.day,
                    time=slot.time,
                    duration_hours=self._duration_hours,
                    basket_url=basket_url,
                )
            )
            return 0
        except Exception:
            traceback.print_exc()
            return 1

    def _poll_until_found_or_timeout(self) -> Slot | None:
        release_at = _today_release_time(self._now(), self._release_hour)
        deadline = release_at + RETRY_WINDOW

        while True:
            slot = self._scanner.scan()
            if slot is not None:
                return slot
            if self._now() >= deadline:
                return None
            self._sleep(poll_interval_seconds(self._now(), release_at))


def poll_interval_seconds(now: datetime, release_at: datetime) -> float:
    if now >= release_at:
        return 10
    if now >= release_at - timedelta(seconds=30):
        return 1
    return 5


def _today_release_time(now: datetime, release_hour: int = 20) -> datetime:
    return now.replace(hour=release_hour, minute=0, second=0, microsecond=0)


def main() -> int:
    from playwright.sync_api import sync_playwright  # noqa: import-outside-toplevel

    config = load_config()
    priorities = build_priorities(config.booking_days, config.preferred_times)

    if config.notify_method == "ntfy":
        notifier = NtfyNotifier(config.ntfy_topic)
    else:
        from twilio.rest import Client as TwilioClient  # noqa: import-outside-toplevel

        twilio_client = TwilioClient(config.twilio_account_sid, config.twilio_auth_token)
        notifier = Notifier(
            twilio_client=twilio_client,
            from_number=config.twilio_from,
            recipients=config.sms_recipients,
        )

    try:
        with sync_playwright() as p:
            factory = playwright_browser_factory(p, headless=True)
            session_manager = SessionManager(
                config=config,
                browser_factory=factory,
                login_flow=clubspark_login,
            )
            session = session_manager.launch()

            scanner = CourtScanner(
                availability_probe=make_playwright_probe(session.page),
                courts=config.courts,
                priorities=priorities,
            )
            basket = BasketManager(session.page, duration_minutes=config.slot_duration_hours * 60)

            return Scheduler(
                scanner, basket, notifier,
                duration_hours=config.slot_duration_hours,
                release_hour=config.release_hour,
            ).run()
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
