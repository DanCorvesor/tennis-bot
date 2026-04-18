from dataclasses import dataclass
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
        raise NotImplementedError


def build_priorities(days: list[str], times: list[str]) -> list[tuple[str, str]]:
    """Preferred times outer, booking days inner.

    With days=[Sat, Sun] and times=[10:00, 11:00, 09:00] this yields
    (Sat,10), (Sun,10), (Sat,11), (Sun,11), (Sat,09), (Sun,09).
    """
    raise NotImplementedError


def court_name_from_url(url: str) -> str:
    raise NotImplementedError
