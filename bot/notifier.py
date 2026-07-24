from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SlotFound:
    court_name: str
    day: str
    time: str
    duration_hours: int
    basket_url: str
    date_str: str = ""


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
        body = (
            f"Tennis slot: {slot.court_name}, {slot.day} {time_range}. "
            f"Booking link: {slot.basket_url}"
        )
        self._broadcast(body)

    def send_slots(self, slots: list[SlotFound]) -> None:
        for day_label, lines in _group_by_day(slots):
            body = f"Tennis slots {day_label}:\n" + "\n".join(lines)
            self._broadcast(body)

    def send_nothing_available(self) -> None:
        self._broadcast(
            "No tennis slots found this week after the full retry window."
        )

    def _broadcast(self, body: str) -> None:
        for _, number in self._recipients:
            self._client.messages.create(
                from_=self._from,
                to=number,
                body=body,
            )


def _group_by_day(slots: list[SlotFound]) -> list[tuple[str, list[str]]]:
    """Group slots by day (preserving order), returning (day_label, lines)
    where each line is 'Court TIME-RANGE: url'."""
    groups: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    order: list[str] = []
    for s in slots:
        key = f"{s.day}|{s.date_str}"
        if key not in groups:
            groups[key] = []
            labels[key] = f"{s.day} ({s.date_str})" if s.date_str else s.day
            order.append(key)
        time_range = _format_time_range(s.time, s.duration_hours)
        groups[key].append(f"{s.court_name} {time_range}: {s.basket_url}")
    return [(labels[k], groups[k]) for k in order]


class NtfyNotifier:
    def __init__(self, topic_prefix: str) -> None:
        self._prefix = topic_prefix

    def _publish(self, title: str, body: str, click: str | None = None) -> None:
        url = f"https://ntfy.sh/{self._prefix}"
        req = Request(url, data=body.encode())
        req.add_header("Title", title)
        req.add_header("Priority", "high")
        req.add_header("Tags", "tennis")
        if click:
            req.add_header("Click", click)
            req.add_header("Actions", f"view, Book now, {click}")
        urlopen(req)

    def send_slot_found(self, slot: SlotFound) -> None:
        # Single slot (release window): keep it simple.
        time_range = _format_time_range(slot.time, slot.duration_hours)
        title = f"Tennis slot: {slot.court_name}, {slot.day} {time_range}"
        body = f"Time: {time_range}\nBooking link: {slot.basket_url}"
        self._publish(title, body, click=slot.basket_url)

    def send_slots(self, slots: list[SlotFound]) -> None:
        # One message per day, listing every available slot with its link.
        for day_label, lines in _group_by_day(slots):
            title = f"Tennis: {day_label} — {len(lines)} slot(s)"
            body = "\n".join(lines)
            self._publish(title, body)

    def send_nothing_available(self) -> None:
        url = f"https://ntfy.sh/{self._prefix}"
        req = Request(
            url,
            data=b"No tennis slots found this week after the full retry window.",
        )
        req.add_header("Title", "No tennis slots")
        req.add_header("Priority", "low")
        urlopen(req)
