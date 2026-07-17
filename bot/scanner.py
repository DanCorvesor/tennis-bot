import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Slot:
    court_name: str
    venue_slug: str
    day: str
    time: str
    booking_url: str


AvailabilityProbe = Callable[[str, str, str], Slot | None]


class CourtScanner:
    """Scans each court URL for the highest-priority available slot."""

    def __init__(
        self,
        availability_probe: AvailabilityProbe,
        courts: list[str],
        priorities: list[tuple[str, str]],
    ) -> None:
        self._probe = availability_probe
        self._courts = courts
        self._priorities = priorities

    def scan(self) -> Slot | None:
        if hasattr(self._probe, "clear_cache"):
            self._probe.clear_cache()
        for day, time in self._priorities:
            for court_url in self._courts:
                slot = self._probe(court_url, day, time)
                if slot:
                    return slot
        return None


def build_priorities(
    schedule: list[tuple[list[str], list[str]]],
) -> list[tuple[str, str]]:
    priorities: list[tuple[str, str]] = []
    for days, times in schedule:
        for time in times:
            for day in days:
                priorities.append((day, time))
    return priorities


def court_name_from_url(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"(?<!^)(?=[A-Z])", " ", slug)


def _venue_slug(court_url: str) -> str:
    return court_url.rstrip("/").rsplit("/", 1)[-1]


def _time_to_minutes(time: str) -> int:
    hours, mins = time.split(":")
    return int(hours) * 60 + int(mins)


def make_playwright_probe(page, duration_minutes: int = 60, today: date | None = None):
    _fixed_today = today
    _last_page_key = [None]

    def clear_cache() -> None:
        _last_page_key[0] = None

    def probe(court_url: str, day: str, time: str) -> Slot | None:
        slug = _venue_slug(court_url)
        ref = _fixed_today or date.today()
        target = _next_weekday(ref, day)
        date_str = target.isoformat()
        name = court_name_from_url(court_url)

        page_key = (slug, date_str)
        if page_key != _last_page_key[0]:
            base = f"{court_url.rstrip('/')}/Booking/BookByDate"
            full_url = f"{base}#?date={date_str}&role=member"
            log.info("Fetching %s %s", name, date_str)
            try:
                current_base = page.url.split("#")[0]
                if current_base != base:
                    page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_function(
                        "document.title !== 'Just a moment...'", timeout=30000,
                    )
                    accept_btn = page.get_by_role("button", name="Accept All")
                    if accept_btn.is_visible():
                        accept_btn.click()
                    page.locator(".time-slot").first.wait_for(timeout=30000)
                else:
                    page.evaluate(
                        f"window.location.hash = '?date={date_str}&role=member'"
                    )
                    page.wait_for_timeout(3000)
                _last_page_key[0] = page_key
            except Exception as exc:
                log.warning("Failed to load %s %s: %s", name, date_str, exc)
                _last_page_key[0] = None
                return None

        minutes = _time_to_minutes(time)
        slot_link = page.locator(
            f'a.book-interval.not-booked[data-test-id$="|{minutes}"]'
        ).first

        if slot_link.count() == 0:
            log.info("No slot: %s %s %s", name, day, time)
            return None

        log.info("AVAILABLE: %s %s %s on %s", name, day, time, date_str)
        booking_page = (
            f"https://clubspark.lta.org.uk/{slug}/Booking/BookByDate"
            f"#?date={date_str}&role=member"
        )
        return Slot(
            court_name=name,
            venue_slug=slug,
            day=day,
            time=time,
            booking_url=booking_page,
        )

    probe.clear_cache = clear_cache
    return probe


_WEEKDAY_INDEX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def _next_weekday(ref: date, day: str) -> date:
    target = _WEEKDAY_INDEX[day]
    offset = (target - ref.weekday()) % 7
    if offset == 0:
        offset = 7
    return ref + timedelta(days=offset)
