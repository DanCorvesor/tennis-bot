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


def make_playwright_probe(page, today: date | None = None):
    """Build an availability probe that asks a Playwright page for a given (court, day, time).

    The probe navigates to the court's booking page for the target date and looks for
    a 1-hour "Book" link at the requested time. Returns the booking URL or None.
    """
    ref = today or date.today()

    def probe(court_url: str, day: str, time: str) -> str | None:
        target = _next_weekday(ref, day)
        url = f"{court_url.rstrip('/')}/Booking/BookByDate#?date={target.isoformat()}&role=member"
        page.goto(url, wait_until="networkidle")

        book_link = page.locator(
            f'a.book-interval:not(.unavailable):has-text("{time}")'
        ).first
        if book_link.count() == 0:
            return None
        href = book_link.get_attribute("href")
        if not href:
            return None
        if href.startswith("/"):
            return f"https://clubspark.lta.org.uk{href}"
        return href

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
