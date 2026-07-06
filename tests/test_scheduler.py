from datetime import datetime, timedelta
from unittest.mock import MagicMock

from bot.notifier import SlotFound
from bot.scanner import Slot
from bot.scheduler import Scheduler, poll_interval_seconds


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self.t = start
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += timedelta(seconds=seconds)


def _slot() -> Slot:
    return Slot(
        court_name="Southwark Park",
        venue_slug="SouthwarkPark",
        day="Saturday",
        time="10:00",
        booking_url="https://clubspark.lta.org.uk/SouthwarkPark/Booking/Book?test=1",
    )


def _pre_release_clock() -> FakeClock:
    return FakeClock(datetime(2026, 4, 18, 19, 58, 0))


def _post_release_clock() -> FakeClock:
    return FakeClock(datetime(2026, 4, 18, 20, 0, 0))


def test_slot_found_triggers_notifier():
    scanner = MagicMock()
    scanner.scan.return_value = _slot()
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc == 0
    notifier.send_slot_found.assert_called_once()
    sent = notifier.send_slot_found.call_args.args[0]
    assert isinstance(sent, SlotFound)
    assert sent.court_name == "Southwark Park"
    assert sent.day == "Saturday"
    assert sent.time == "10:00"
    assert "SouthwarkPark/Booking/Book" in sent.basket_url
    notifier.send_nothing_available.assert_not_called()


def test_nothing_available_after_timeout():
    scanner = MagicMock()
    scanner.scan.return_value = None
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc == 0
    notifier.send_nothing_available.assert_called_once()
    notifier.send_slot_found.assert_not_called()


def test_scanner_exception_exits_nonzero():
    scanner = MagicMock()
    scanner.scan.side_effect = RuntimeError("API failed")
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc != 0
    notifier.send_slot_found.assert_not_called()


def test_polls_for_5_minutes_at_10s_intervals_after_8pm():
    scanner = MagicMock()
    scanner.scan.return_value = None
    notifier = MagicMock()

    clock = _post_release_clock()
    Scheduler(scanner, notifier, now=clock.now, sleep=clock.sleep).run()

    assert scanner.scan.call_count >= 30
    assert all(s == 10 for s in clock.sleeps)
    assert sum(clock.sleeps) >= 300


def test_ramps_polling_frequency_approaching_8pm():
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 58, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 5
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 59, 30), datetime(2026, 4, 18, 20, 0, 0)
    ) == 1
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 20, 0, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 10


def test_no_real_sleep_or_network_in_tests():
    scanner = MagicMock()
    scanner.scan.return_value = _slot()
    notifier = MagicMock()

    clock = _pre_release_clock()
    Scheduler(scanner, notifier, now=clock.now, sleep=clock.sleep).run()

    assert clock.sleeps == []
