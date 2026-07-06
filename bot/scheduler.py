import time
import traceback
from datetime import datetime, timedelta
from typing import Callable

from bot.config import load_config
from bot.notifier import Notifier, NtfyNotifier, SlotFound
from bot.scanner import CourtScanner, Slot, build_priorities, make_api_probe


RETRY_WINDOW = timedelta(minutes=5)


class Scheduler:
    """Orchestrates the polling lifecycle around the 8pm slot release."""

    def __init__(
        self,
        scanner: CourtScanner,
        notifier,
        *,
        duration_hours: int = 1,
        release_hour: int = 20,
        now: Callable[[], datetime] = datetime.now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._scanner = scanner
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

            self._notifier.send_slot_found(
                SlotFound(
                    court_name=slot.court_name,
                    day=slot.day,
                    time=slot.time,
                    duration_hours=self._duration_hours,
                    basket_url=slot.booking_url,
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

    scanner = CourtScanner(
        availability_probe=make_api_probe(
            duration_minutes=config.slot_duration_hours * 60,
        ),
        courts=config.courts,
        priorities=priorities,
    )

    return Scheduler(
        scanner,
        notifier,
        duration_hours=config.slot_duration_hours,
        release_hour=config.release_hour,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
