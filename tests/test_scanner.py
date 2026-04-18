from unittest.mock import MagicMock

import pytest

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


def probe_returning(available: dict[tuple[str, str, str], str]):
    def _probe(court_url: str, day: str, time: str):
        return available.get((court_url, day, time))

    return _probe


def test_returns_highest_priority_available_slot():
    available = {
        (COURTS[0], "Sunday", "10:00"): "https://book/sun10-southwark",
        (COURTS[1], "Saturday", "10:00"): "https://book/sat10-brunswick",
        (COURTS[2], "Saturday", "11:00"): "https://book/sat11-burgess",
    }
    scanner = CourtScanner(probe_returning(available), COURTS, PRIORITIES)

    result = scanner.scan()

    assert result == Slot(
        court_name=court_name_from_url(COURTS[1]),
        court_url=COURTS[1],
        day="Saturday",
        time="10:00",
        booking_url="https://book/sat10-brunswick",
    )


def test_skips_unavailable_slots_and_falls_through():
    available = {
        (COURTS[2], "Saturday", "11:00"): "https://book/sat11-burgess",
    }
    scanner = CourtScanner(probe_returning(available), COURTS, PRIORITIES)

    result = scanner.scan()

    assert result is not None
    assert result.day == "Saturday"
    assert result.time == "11:00"
    assert result.court_url == COURTS[2]


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

    # First three calls must all be Saturday 10:00 across every court
    assert [c[1:] for c in call_order[:3]] == [("Saturday", "10:00")] * 3
    assert {c[0] for c in call_order[:3]} == set(COURTS)

    # Next three are the second priority (Sunday 10:00) across all courts
    assert [c[1:] for c in call_order[3:6]] == [("Sunday", "10:00")] * 3


def test_short_circuits_on_first_match_without_probing_lower_priorities():
    probe = MagicMock(return_value="https://book/first")
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
    # Sanity: the scanner must accept any callable as availability probe.
    calls: list = []
    scanner = CourtScanner(lambda *a: calls.append(a) or None, COURTS, PRIORITIES)
    scanner.scan()
    assert calls
