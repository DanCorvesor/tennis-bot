import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Callable

log = logging.getLogger(__name__)

from bot.config import load_config
from bot.notifier import Notifier, NtfyNotifier, SlotFound
from bot.scanner import CourtScanner, Slot, build_priorities, make_probe


RETRY_WINDOW = timedelta(minutes=5)
HOURLY_START = 8
HOURLY_END = 22


class Scheduler:
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
        # Slots already alerted in general checks, so we don't re-notify the
        # same bookable slot every cycle. Keyed by (venue, date, time).
        self._notified: set[tuple[str, str, str]] = set()

    def run_forever(self) -> None:
        log.info(
            "Bot started — release polling at %d:00, "
            "hourly checks %d:00-%d:00",
            self._release_hour, HOURLY_START, HOURLY_END,
        )
        while True:
            try:
                self._run_day()
            except Exception:
                log.exception("Error during daily run")
            self._sleep_until_next_window()

    def _run_day(self) -> None:
        now = self._now()
        hour = now.hour

        if self._in_release_window(now):
            self._poll_release()
        elif HOURLY_START <= hour < HOURLY_END:
            self._poll_once("hourly check")
        else:
            log.info("Outside active hours (%d:00-%d:00), sleeping", HOURLY_START, HOURLY_END)

    def _poll_release(self) -> None:
        release_at = self._now().replace(
            hour=self._release_hour, minute=0, second=0, microsecond=0,
        )
        deadline = release_at + RETRY_WINDOW

        log.info("Release window — polling until %s", deadline.strftime("%H:%M:%S"))
        poll_count = 0
        while True:
            poll_count += 1
            slot = self._scanner.scan()
            if slot is not None:
                self._notify_slot(slot)
                return
            if self._now() >= deadline:
                log.info("Release window ended after %d polls, no slots", poll_count)
                self._notifier.send_nothing_available()
                return
            interval = poll_interval_seconds(self._now(), release_at)
            log.info("Poll %d, sleeping %ss", poll_count, interval)
            self._sleep(interval)

    def _poll_once(self, label: str) -> None:
        log.info("Running %s", label)
        slots = self._scanner.scan_all()
        if not slots:
            log.info("No slots found")
            return
        new = [s for s in slots if self._slot_key(s) not in self._notified]
        log.info("%d slot(s) available, %d new", len(slots), len(new))
        if not new:
            return
        # One notification per day, listing every new slot for that day.
        self._notifier.send_slots([self._to_slot_found(s) for s in new])
        for slot in new:
            self._notified.add(self._slot_key(slot))

    @staticmethod
    def _slot_key(slot: Slot) -> tuple[str, str, str]:
        return (slot.venue_slug, slot.date_str, slot.time)

    def _to_slot_found(self, slot: Slot) -> SlotFound:
        return SlotFound(
            court_name=slot.court_name,
            day=slot.day,
            time=slot.time,
            duration_hours=self._duration_hours,
            basket_url=slot.booking_url,
            date_str=slot.date_str,
        )

    def _notify_slot(self, slot: Slot) -> None:
        log.info("Slot found: %s %s %s", slot.court_name, slot.day, slot.time)
        self._notified.add(self._slot_key(slot))
        self._notifier.send_slot_found(self._to_slot_found(slot))

    def _in_release_window(self, now: datetime) -> bool:
        release_at = now.replace(
            hour=self._release_hour, minute=0, second=0, microsecond=0,
        )
        window_start = release_at - timedelta(minutes=2)
        window_end = release_at + RETRY_WINDOW
        return window_start <= now <= window_end

    def _sleep_until_next_window(self) -> None:
        now = self._now()
        hour = now.hour

        if self._in_release_window(now):
            return

        if HOURLY_START <= hour < HOURLY_END:
            next_check = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0,
            )
        elif hour < HOURLY_START:
            next_check = now.replace(
                hour=HOURLY_START, minute=0, second=0, microsecond=0,
            )
        else:
            tomorrow = now + timedelta(days=1)
            next_check = tomorrow.replace(
                hour=HOURLY_START, minute=0, second=0, microsecond=0,
            )

        wait = (next_check - now).total_seconds()
        log.info("Next check at %s (in %dm)", next_check.strftime("%H:%M"), int(wait / 60))
        self._sleep(wait)


def poll_interval_seconds(now: datetime, release_at: datetime) -> float:
    if now >= release_at:
        return 10
    if now >= release_at - timedelta(seconds=30):
        return 1
    return 5


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    config = load_config()
    priorities = build_priorities(config.schedule)

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

    import os

    from bot.browser import BrowserSession

    # nodriver drives real Chrome directly over the DevTools socket, avoiding
    # the CDP automation fingerprint that gets Playwright blocked by Cloudflare.
    # A persistent profile keeps the cf_clearance cookie between runs. Runs
    # headful under Xvfb by default (see Dockerfile); HEADLESS=1 forces headless.
    profile_dir = os.environ.get("BROWSER_PROFILE_DIR", "/app/.state/chrome-profile")
    executable_path = os.environ.get("BROWSER_EXECUTABLE_PATH") or None
    headless = os.environ.get("HEADLESS") == "1"

    session = BrowserSession(
        profile_dir=profile_dir,
        headless=headless,
        executable_path=executable_path,
    )
    session.start()

    scanner = CourtScanner(
        availability_probe=make_probe(
            session,
            duration_minutes=config.slot_duration_hours * 60,
        ),
        courts=config.courts,
        priorities=priorities,
    )

    try:
        Scheduler(
            scanner,
            notifier,
            duration_hours=config.slot_duration_hours,
            release_hour=config.release_hour,
        ).run_forever()
    finally:
        session.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
