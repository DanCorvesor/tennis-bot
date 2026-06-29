import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable


@dataclass(frozen=True)
class Slot:
    court_name: str
    court_url: str
    day: str
    time: str
    booking_url: str


AvailabilityProbe = Callable[[str, str, str], str | None]


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
        for day, time in self._priorities:
            for court_url in self._courts:
                booking_url = self._probe(court_url, day, time)
                if booking_url:
                    return Slot(
                        court_name=court_name_from_url(court_url),
                        court_url=court_url,
                        day=day,
                        time=time,
                        booking_url=booking_url,
                    )
        return None


def build_priorities(days: list[str], times: list[str]) -> list[tuple[str, str]]:
    return [(day, time) for time in times for day in days]


def court_name_from_url(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"(?<!^)(?=[A-Z])", " ", slug)


def _time_to_minutes(time: str) -> int:
    hours, mins = time.split(":")
    return int(hours) * 60 + int(mins)


def make_playwright_probe(page, today: date | None = None):
    ref = today or date.today()

    last_url = [None]

    def probe(court_url: str, day: str, time: str) -> str | None:
        target = _next_weekday(ref, day)
        base = f"{court_url.rstrip('/')}/Booking/BookByDate"
        url = f"{base}#?date={target.isoformat()}&role=member"

        if url != last_url[0]:
            current_base = page.url.split("#")[0]
            if current_base != base:
                page.goto(url)
                page.locator(".time-slot").first.wait_for(timeout=30_000)
            page.evaluate(
                f"window.location.hash = '?date={target.isoformat()}&role=member'"
            )
            page.wait_for_timeout(3000)
            last_url[0] = url

        minutes = _time_to_minutes(time)
        slot_link = page.locator(
            f'a.book-interval.not-booked[data-test-id$="|{minutes}"]'
        ).first
        if slot_link.count() == 0:
            return None
        return slot_link.get_attribute("data-test-id")

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
