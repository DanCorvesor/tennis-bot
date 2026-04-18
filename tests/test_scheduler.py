from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

import pytest

from bot.basket import SlotUnavailableError
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
        court_url="https://clubspark.lta.org.uk/SouthwarkPark",
        day="Saturday",
        time="10:00",
        booking_url="https://clubspark.lta.org.uk/book/abc",
    )


def _pre_release_clock() -> FakeClock:
    return FakeClock(datetime(2026, 4, 18, 19, 58, 0))


def _post_release_clock() -> FakeClock:
    return FakeClock(datetime(2026, 4, 18, 20, 0, 0))


def test_slot_found_triggers_basket_then_notifier():
    scanner = MagicMock()
    scanner.scan.return_value = _slot()
    basket = MagicMock()
    basket.add_to_basket.return_value = "https://clubspark.lta.org.uk/basket/xyz"
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc == 0
    basket.add_to_basket.assert_called_once_with("https://clubspark.lta.org.uk/book/abc")
    notifier.send_slot_found.assert_called_once()
    sent = notifier.send_slot_found.call_args.args[0]
    assert isinstance(sent, SlotFound)
    assert sent.court_name == "Southwark Park"
    assert sent.day == "Saturday"
    assert sent.time == "10:00"
    assert sent.basket_url == "https://clubspark.lta.org.uk/basket/xyz"
    notifier.send_nothing_available.assert_not_called()
    notifier.send_error.assert_not_called()


def test_nothing_available_after_timeout():
    scanner = MagicMock()
    scanner.scan.return_value = None
    basket = MagicMock()
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc == 0
    notifier.send_nothing_available.assert_called_once()
    notifier.send_slot_found.assert_not_called()
    notifier.send_error.assert_not_called()
    basket.add_to_basket.assert_not_called()


def test_scanner_exception_sends_error_and_exits_nonzero():
    scanner = MagicMock()
    scanner.scan.side_effect = RuntimeError("LTA login failed")
    basket = MagicMock()
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc != 0
    notifier.send_error.assert_called_once()
    description = notifier.send_error.call_args.args[0]
    assert "LTA login failed" in description


def test_basket_exception_sends_error():
    scanner = MagicMock()
    scanner.scan.return_value = _slot()
    basket = MagicMock()
    basket.add_to_basket.side_effect = SlotUnavailableError("slot gone")
    notifier = MagicMock()

    clock = _pre_release_clock()
    rc = Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    assert rc != 0
    notifier.send_error.assert_called_once()
    assert "slot gone" in notifier.send_error.call_args.args[0]


def test_polls_for_5_minutes_at_10s_intervals_after_8pm():
    scanner = MagicMock()
    scanner.scan.return_value = None
    basket = MagicMock()
    notifier = MagicMock()

    clock = _post_release_clock()
    Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    # At 20:00 with 10s intervals for 5 minutes, we expect ~30 poll attempts.
    assert scanner.scan.call_count >= 30
    # All post-release sleeps are 10s.
    assert all(s == 10 for s in clock.sleeps)
    # Total elapsed is at least 5 minutes.
    assert sum(clock.sleeps) >= 300


def test_ramps_polling_frequency_approaching_8pm():
    # At 19:58 → 5s intervals. At 19:59:30 → 1s. At 20:00 → 10s.
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 58, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 5
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 59, 15), datetime(2026, 4, 18, 20, 0, 0)
    ) == 5
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 59, 30), datetime(2026, 4, 18, 20, 0, 0)
    ) == 1
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 59, 59), datetime(2026, 4, 18, 20, 0, 0)
    ) == 1
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 20, 0, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 10
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 20, 3, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 10


def test_scanner_and_basket_not_called_on_nothing_available_path():
    scanner = MagicMock()
    scanner.scan.return_value = None
    basket = MagicMock()
    notifier = MagicMock()

    clock = _pre_release_clock()
    Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    basket.add_to_basket.assert_not_called()


def test_no_real_sleep_or_network_in_tests():
    scanner = MagicMock()
    scanner.scan.return_value = _slot()
    basket = MagicMock()
    basket.add_to_basket.return_value = "https://clubspark.lta.org.uk/basket/xyz"
    notifier = MagicMock()

    clock = _pre_release_clock()
    Scheduler(scanner, basket, notifier, now=clock.now, sleep=clock.sleep).run()

    # With a slot on first scan, no sleep is needed before bailing out.
    assert clock.sleeps == []
