import json
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


def _build_booking_url(
    venue_slug: str,
    resource_id: str,
    resource_group_id: str,
    session_id: str,
    date_str: str,
    start_time: int,
    end_time: int,
    category: int,
    sub_category: int,
) -> str:
    from urllib.parse import urlencode

    params = {
        "Contacts[0].IsPrimary": "true",
        "Contacts[0].IsJunior": "false",
        "Contacts[0].IsPlayer": "true",
        "ResourceID": resource_id,
        "Date": date_str,
        "SessionID": session_id,
        "StartTime": start_time,
        "EndTime": end_time,
        "Category": category,
        "SubCategory": sub_category,
        "VenueID": resource_group_id,
        "ResourceGroupID": resource_group_id,
    }
    base = f"https://clubspark.lta.org.uk/{venue_slug}/Booking/Book"
    return f"{base}?{urlencode(params)}"


def make_api_probe(duration_minutes: int = 60, today: date | None = None):
    _fixed_today = today
    cache: dict[tuple[str, str], dict] = {}
    _page = [None]

    def _get_page():
        if _page[0] is None or _page[0].is_closed():
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--headless=new"],
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
            _page[0] = page
        return _page[0]

    def _fetch_json(page, url: str) -> dict | None:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_function(
            "document.title !== 'Just a moment...'", timeout=20000,
        )
        body = page.inner_text("body")
        return json.loads(body)

    def clear_cache() -> None:
        cache.clear()

    def probe(court_url: str, day: str, time: str) -> Slot | None:
        slug = _venue_slug(court_url)
        ref = _fixed_today or date.today()
        target = _next_weekday(ref, day)
        date_str = target.isoformat()

        cache_key = (slug, date_str)
        if cache_key not in cache:
            api_url = (
                f"https://clubspark.lta.org.uk/v0/VenueBooking/{slug}"
                f"/GetVenueSessions?resourceID=&startDate={date_str}"
                f"&endDate={date_str}&roleId="
            )
            log.info("Fetching %s %s", court_name_from_url(court_url), date_str)
            try:
                page = _get_page()
                data = _fetch_json(page, api_url)
                if data is None:
                    return None
                cache[cache_key] = data
            except Exception as exc:
                log.warning("API request failed for %s %s: %s", slug, date_str, exc)
                return None

        data = cache[cache_key]
        rg_id = data["ResourceGroups"][0]["ID"]
        start_minutes = _time_to_minutes(time)
        end_minutes = start_minutes + duration_minutes
        name = court_name_from_url(court_url)

        for resource in data["Resources"]:
            for session in resource["Days"][0]["Sessions"]:
                if (
                    session["Category"] == 0
                    and "Cost" in session
                    and session["StartTime"] == start_minutes
                ):
                    log.info(
                        "AVAILABLE: %s %s %s %s on %s",
                        name, resource["Name"], day, time, date_str,
                    )
                    return Slot(
                        court_name=name,
                        venue_slug=slug,
                        day=day,
                        time=time,
                        booking_url=_build_booking_url(
                            venue_slug=slug,
                            resource_id=resource["ID"],
                            resource_group_id=rg_id,
                            session_id=session["ID"],
                            date_str=date_str,
                            start_time=start_minutes,
                            end_time=end_minutes,
                            category=session["Category"],
                            sub_category=session["SubCategory"],
                        ),
                    )

        log.info("No slot: %s %s %s", name, day, time)
        return None

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
