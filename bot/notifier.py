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
        raise NotImplementedError

    def send_nothing_available(self) -> None:
        raise NotImplementedError

    def send_error(self, description: str) -> None:
        raise NotImplementedError
