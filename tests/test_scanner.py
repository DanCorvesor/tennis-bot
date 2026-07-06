from unittest.mock import MagicMock

from bot.scanner import (
    CourtScanner,
    Slot,
    build_priorities,
    court_name_from_url,
)


COURTS = [
    "https://clubspark.lta.org.uk/SouthwarkPark",
    "https://clubspark.lta.org.uk/BrunswickPark",
    "https://clubspark.lta.org.uk/BurgessParkSouthwark",
]
PRIORITIES = [
    ("Saturday", "10:00"),
    ("Sunday", "10:00"),
    ("Saturday", "11:00"),
    ("Sunday", "11:00"),
    ("Saturday", "09:00"),
    ("Sunday", "09:00"),
]


def _slot(court_url, day, time):
    slug = court_url.rstrip("/").rsplit("/", 1)[-1]
    return Slot(
        court_name=court_name_from_url(court_url),
        venue_slug=slug,
        day=day,
        time=time,
        booking_url=f"https://clubspark.lta.org.uk/{slug}/Booking/Book?test=1",
    )


def probe_returning(available: dict[tuple[str, str, str], Slot]):
    def _probe(court_url: str, day: str, time: str):
        return available.get((court_url, day, time))

    return _probe


def test_returns_highest_priority_available_slot():
    available = {
        (COURTS[0], "Sunday", "10:00"): _slot(COURTS[0], "Sunday", "10:00"),
        (COURTS[1], "Saturday", "10:00"): _slot(COURTS[1], "Saturday", "10:00"),
        (COURTS[2], "Saturday", "11:00"): _slot(COURTS[2], "Saturday", "11:00"),
    }
    scanner = CourtScanner(probe_returning(available), COURTS, PRIORITIES)

    result = scanner.scan()

    assert result.venue_slug == "BrunswickPark"
    assert result.day == "Saturday"
    assert result.time == "10:00"


def test_skips_unavailable_slots_and_falls_through():
    available = {
        (COURTS[2], "Saturday", "11:00"): _slot(COURTS[2], "Saturday", "11:00"),
    }
    scanner = CourtScanner(probe_returning(available), COURTS, PRIORITIES)

    result = scanner.scan()

    assert result is not None
    assert result.day == "Saturday"
    assert result.time == "11:00"
    assert result.venue_slug == "BurgessParkSouthwark"


def test_returns_none_when_nothing_available():
    scanner = CourtScanner(probe_returning({}), COURTS, PRIORITIES)
    assert scanner.scan() is None


def test_checks_all_courts_per_priority_before_next_priority():
    call_order: list[tuple[str, str, str]] = []

    def probe(court_url, day, time):
        call_order.append((court_url, day, time))
        return None

    scanner = CourtScanner(probe, COURTS, PRIORITIES)
    scanner.scan()

    assert [c[1:] for c in call_order[:3]] == [("Saturday", "10:00")] * 3
    assert {c[0] for c in call_order[:3]} == set(COURTS)
    assert [c[1:] for c in call_order[3:6]] == [("Sunday", "10:00")] * 3


def test_short_circuits_on_first_match_without_probing_lower_priorities():
    slot = _slot(COURTS[0], "Saturday", "10:00")
    probe = MagicMock(return_value=slot)
    scanner = CourtScanner(probe, COURTS, PRIORITIES)

    result = scanner.scan()

    assert result is not None
    assert probe.call_count == 1
    probe.assert_called_once_with(COURTS[0], "Saturday", "10:00")


def test_build_priorities_matches_prd_order():
    assert build_priorities(["Saturday", "Sunday"], ["10:00", "11:00", "09:00"]) == PRIORITIES


def test_court_name_from_url_is_readable():
    name = court_name_from_url("https://clubspark.lta.org.uk/SouthwarkPark")
    assert "Southwark" in name
    assert "Park" in name


def test_no_live_http_in_scanner_tests():
    calls: list = []
    scanner = CourtScanner(lambda *a: calls.append(a) or None, COURTS, PRIORITIES)
    scanner.scan()
    assert calls
