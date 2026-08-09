from datetime import datetime, timedelta
from unittest.mock import MagicMock

from bot.notifier import SlotFound
from bot.scanner import CourtScanner, Slot, slot_key
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


def _scheduler(scanner, notifier, clock, release_hour=20):
    return Scheduler(
        scanner,
        notifier,
        release_hour=release_hour,
        now=clock.now,
        sleep=clock.sleep,
    )


def test_release_window_finds_slot_and_notifies():
    scanner = MagicMock()
    scanner.scan.return_value = _slot()
    notifier = MagicMock()

    clock = FakeClock(datetime(2026, 4, 18, 20, 0, 0))
    _scheduler(scanner, notifier, clock)._poll_release()

    notifier.send_slot_found.assert_called_once()
    sent = notifier.send_slot_found.call_args.args[0]
    assert isinstance(sent, SlotFound)
    assert sent.court_name == "Southwark Park"


def _always_available_scanner(slot: Slot) -> CourtScanner:
    return CourtScanner(
        lambda *args: slot,
        courts=["https://clubspark.lta.org.uk/SouthwarkPark"],
        priorities=[("Saturday", "10:00")],
    )


def test_release_window_skips_already_notified_slot():
    slot = _slot()
    notifier = MagicMock()
    clock = FakeClock(datetime(2026, 4, 18, 20, 0, 0))
    s = _scheduler(_always_available_scanner(slot), notifier, clock)
    s._notified.add(slot_key(slot))

    s._poll_release()

    notifier.send_slot_found.assert_not_called()
    notifier.send_nothing_available.assert_called_once()


def test_release_window_notifies_once_then_sleeps_out_window():
    slot = _slot()
    notifier = MagicMock()
    clock = FakeClock(datetime(2026, 4, 18, 20, 0, 0))
    s = _scheduler(_always_available_scanner(slot), notifier, clock)

    s._poll_release()
    notifier.send_slot_found.assert_called_once()
    # Slept past the retry window, so run_forever won't re-enter the
    # release poll and re-send the same slot.
    assert not s._in_release_window(clock.t)

    # Next day's release: same slot still free — no repeat notification.
    clock.t = datetime(2026, 4, 19, 20, 0, 0)
    s._poll_release()
    notifier.send_slot_found.assert_called_once()
    notifier.send_nothing_available.assert_called_once()


def test_release_window_sends_nothing_after_timeout():
    scanner = MagicMock()
    scanner.scan.return_value = None
    notifier = MagicMock()

    clock = FakeClock(datetime(2026, 4, 18, 20, 0, 0))
    _scheduler(scanner, notifier, clock)._poll_release()

    notifier.send_nothing_available.assert_called_once()
    assert scanner.scan.call_count >= 30
    assert all(s == 10 for s in clock.sleeps)


def test_hourly_check_finds_slot():
    scanner = MagicMock()
    scanner.scan_all.return_value = [_slot()]
    notifier = MagicMock()
    notifier.send_slots.side_effect = lambda slots: slots

    clock = FakeClock(datetime(2026, 4, 18, 14, 0, 0))
    scheduler = _scheduler(scanner, notifier, clock)
    scheduler._poll_once("test")

    notifier.send_slots.assert_called_once()
    sent = notifier.send_slots.call_args.args[0]
    assert len(sent) == 1
    assert isinstance(sent[0], SlotFound)

    # Second check: already notified, so nothing is re-sent.
    scheduler._poll_once("test")
    notifier.send_slots.assert_called_once()


def test_hourly_check_no_slot():
    scanner = MagicMock()
    scanner.scan_all.return_value = []
    notifier = MagicMock()

    clock = FakeClock(datetime(2026, 4, 18, 14, 0, 0))
    _scheduler(scanner, notifier, clock)._poll_once("test")

    notifier.send_slots.assert_not_called()
    notifier.send_nothing_available.assert_not_called()


def test_in_release_window_detection():
    clock = FakeClock(datetime(2026, 4, 18, 19, 59, 0))
    s = _scheduler(MagicMock(), MagicMock(), clock)
    assert s._in_release_window(datetime(2026, 4, 18, 19, 58, 0))
    assert s._in_release_window(datetime(2026, 4, 18, 20, 0, 0))
    assert s._in_release_window(datetime(2026, 4, 18, 20, 4, 59))
    assert not s._in_release_window(datetime(2026, 4, 18, 19, 57, 0))
    assert not s._in_release_window(datetime(2026, 4, 18, 20, 6, 0))


def test_sleep_until_next_window_during_active_hours():
    clock = FakeClock(datetime(2026, 4, 18, 14, 30, 0))
    s = _scheduler(MagicMock(), MagicMock(), clock)
    s._sleep_until_next_window()
    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == 1800


def test_sleep_until_next_window_after_hours():
    clock = FakeClock(datetime(2026, 4, 18, 22, 0, 0))
    s = _scheduler(MagicMock(), MagicMock(), clock)
    s._sleep_until_next_window()
    assert len(clock.sleeps) == 1
    assert clock.t.hour == 8
    assert clock.t.day == 19


def test_ramps_polling_frequency_approaching_release():
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 58, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 5
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 19, 59, 30), datetime(2026, 4, 18, 20, 0, 0)
    ) == 1
    assert poll_interval_seconds(
        datetime(2026, 4, 18, 20, 0, 0), datetime(2026, 4, 18, 20, 0, 0)
    ) == 10
