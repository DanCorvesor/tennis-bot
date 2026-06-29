from dataclasses import dataclass


@dataclass(frozen=True)
class SlotFound:
    court_name: str
    day: str
    time: str
    duration_hours: int
    basket_url: str


def _format_time_range(start_24: str, duration_hours: int) -> str:
    start_h, start_m = int(start_24.split(":")[0]), int(start_24.split(":")[1])
    end_h = start_h + duration_hours
    end_m = start_m

    def _ampm(h: int, m: int) -> str:
        suffix = "AM" if h < 12 else "PM"
        display = h if h <= 12 else h - 12
        if display == 0:
            display = 12
        return f"{display}:{m:02d}{suffix}" if m else f"{display}{suffix}"

    return f"{_ampm(start_h, start_m)}-{_ampm(end_h, end_m)}"


class Notifier:
    def __init__(
        self,
        twilio_client,
        from_number: str,
        recipients: list[tuple[str, str]],
    ) -> None:
        self._client = twilio_client
        self._from = from_number
        self._recipients = recipients

    def send_slot_found(self, slot: SlotFound) -> None:
        time_range = _format_time_range(slot.time, slot.duration_hours)
        for name, number in self._recipients:
            body = (
                f"Hey {name}! We've found you a tennis slot! "
                f"{slot.court_name}, {slot.day} {time_range}. "
                f"Be quick to book it, if you are gonna pay, message in the group "
                f"to let everyone know. Link: {slot.basket_url}"
            )
            self._client.messages.create(
                from_=self._from, to=number, body=body
            )

    def send_nothing_available(self) -> None:
        self._broadcast(
            "No tennis slots found this week after the full retry window."
        )

    def send_error(self, description: str) -> None:
        msg = f"Tennis bot error: {description}"
        self._broadcast(msg[:1600])

    def _broadcast(self, body: str) -> None:
        for _, number in self._recipients:
            self._client.messages.create(
                from_=self._from,
                to=number,
                body=body,
            )
