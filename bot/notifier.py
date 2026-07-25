import logging
import time
from dataclasses import dataclass
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)


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
        for court_name, day_label, lines in _group_by_court_day(slots):
            body = f"{court_name} — {day_label}:\n" + "\n".join(lines)
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


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def _group_by_court_day(
    slots: list[SlotFound],
) -> list[tuple[str, str, list[str], list[SlotFound]]]:
    """Group slots by (court, day), preserving order. Returns
    (court_name, day_label, lines, members) where each line is
    'TIME-RANGE: url' and members are the SlotFound objects in that group."""
    lines: dict[tuple[str, str, str], list[str]] = {}
    members: dict[tuple[str, str, str], list[SlotFound]] = {}
    labels: dict[tuple[str, str, str], str] = {}
    order: list[tuple[str, str, str]] = []
    for s in slots:
        key = (s.court_name, s.day, s.date_str)
        if key not in lines:
            lines[key] = []
            members[key] = []
            labels[key] = f"{s.day} ({s.date_str})" if s.date_str else s.day
            order.append(key)
        time_range = _format_time_range(s.time, s.duration_hours)
        lines[key].append(f"{time_range}: {s.basket_url}")
        members[key].append(s)
    return [(k[0], labels[k], lines[k], members[k]) for k in order]


class NtfyNotifier:
    def __init__(self, topic_prefix: str) -> None:
        self._prefix = topic_prefix

    def _topic_for(self, court_name: str) -> str:
        return f"{self._prefix}-{_slugify(court_name)}"

    def _publish(
        self, topic: str, title: str, body: str, click: str | None = None
    ) -> bool:
        url = f"https://ntfy.sh/{topic}"
        req = Request(url, data=body.encode())
        # HTTP headers are latin-1; keep the Title ASCII-safe.
        safe_title = title.encode("ascii", "replace").decode("ascii")
        req.add_header("Title", safe_title)
        req.add_header("Priority", "high")
        req.add_header("Tags", "tennis")
        if click:
            req.add_header("Click", click)
            req.add_header("Actions", f"view, Book now, {click}")
        for attempt in range(3):
            try:
                urlopen(req, timeout=15)
                return True
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "ntfy publish to %s failed (attempt %d/3): %s",
                    topic, attempt + 1, exc,
                )
                time.sleep(2 * (attempt + 1))
        return False

    def send_slot_found(self, slot: SlotFound) -> None:
        # Single slot (release window): keep it simple, on the court's topic.
        time_range = _format_time_range(slot.time, slot.duration_hours)
        title = f"Tennis slot: {slot.court_name}, {slot.day} {time_range}"
        body = f"Time: {time_range}\nBooking link: {slot.basket_url}"
        self._publish(
            self._topic_for(slot.court_name), title, body, click=slot.basket_url
        )

    def send_slots(self, slots: list[SlotFound]) -> list[SlotFound]:
        # One message per court per day, on that court's topic. Returns the
        # slots whose message was sent OK, so callers only dedup those.
        sent: list[SlotFound] = []
        groups = _group_by_court_day(slots)
        for i, (court_name, day_label, lines, members) in enumerate(groups):
            title = f"Tennis: {court_name} {day_label} - {len(lines)} slot(s)"
            body = "\n".join(lines)
            if self._publish(self._topic_for(court_name), title, body):
                sent.extend(members)
            # Space out messages to avoid ntfy.sh rate limiting.
            if i < len(groups) - 1:
                time.sleep(1)
        return sent

    def send_nothing_available(self) -> None:
        url = f"https://ntfy.sh/{self._prefix}"
        req = Request(
            url,
            data=b"No tennis slots found this week after the full retry window.",
        )
        req.add_header("Title", "No tennis slots")
        req.add_header("Priority", "low")
        urlopen(req)
