from dataclasses import dataclass


@dataclass(frozen=True)
class SlotFound:
    court_name: str
    day: str
    time: str
    basket_url: str


class Notifier:
    def __init__(
        self,
        twilio_client,
        from_number: str,
        recipients: list[str],
    ) -> None:
        self._client = twilio_client
        self._from = from_number
        self._recipients = recipients

    def send_slot_found(self, slot: SlotFound) -> None:
        body = (
            f"Tennis slot found: {slot.court_name}, {slot.day} {slot.time}. "
            f"Pay here within a few mins: {slot.basket_url}"
        )
        self._broadcast(body)

    def send_nothing_available(self) -> None:
        self._broadcast(
            "No tennis slots found this week after the full retry window."
        )

    def send_error(self, description: str) -> None:
        msg = f"Tennis bot error: {description}"
        self._broadcast(msg[:1600])

    def _broadcast(self, body: str) -> None:
        for number in self._recipients:
            self._client.messages.create(
                from_=self._from,
                to=number,
                body=body,
            )
