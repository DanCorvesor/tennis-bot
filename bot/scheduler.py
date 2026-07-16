import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Callable

log = logging.getLogger(__name__)

from bot.config import load_config
from bot.notifier import Notifier, NtfyNotifier, SlotFound
from bot.scanner import CourtScanner, Slot, build_priorities, make_playwright_probe


RETRY_WINDOW = timedelta(minutes=5)
HOURLY_START = 9
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
        slot = self._scanner.scan()
        if slot is not None:
            self._notify_slot(slot)
        else:
            log.info("No slots found")

    def _notify_slot(self, slot: Slot) -> None:
        log.info("Slot found: %s %s %s", slot.court_name, slot.day, slot.time)
        self._notifier.send_slot_found(
            SlotFound(
                court_name=slot.court_name,
                day=slot.day,
                time=slot.time,
                duration_hours=self._duration_hours,
                basket_url=slot.booking_url,
            )
        )

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

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=[
                "--headless=new",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.add_init_script(
            'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        )

        scanner = CourtScanner(
            availability_probe=make_playwright_probe(
                page,
                duration_minutes=config.slot_duration_hours * 60,
            ),
            courts=config.courts,
            priorities=priorities,
        )

        Scheduler(
            scanner,
            notifier,
            duration_hours=config.slot_duration_hours,
            release_hour=config.release_hour,
        ).run_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
