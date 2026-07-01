from unittest.mock import MagicMock

import pytest

from bot.notifier import Notifier, SlotFound


FROM = "+14155238886"
RECIPIENTS = [("Alice", "+447512211264"), ("Bob", "+447700900001")]


@pytest.fixture
def twilio_client():
    client = MagicMock()
    client.messages.create = MagicMock()
    return client


@pytest.fixture
def notifier(twilio_client):
    return Notifier(twilio_client=twilio_client, from_number=FROM, recipients=RECIPIENTS)


def _bodies(twilio_client) -> list[str]:
    return [c.kwargs["body"] for c in twilio_client.messages.create.call_args_list]


def _tos(twilio_client) -> list[str]:
    return [c.kwargs["to"] for c in twilio_client.messages.create.call_args_list]


def _froms(twilio_client) -> list[str]:
    return [c.kwargs["from_"] for c in twilio_client.messages.create.call_args_list]


def test_slot_found_sent_to_every_recipient(notifier, twilio_client):
    slot = SlotFound(
        court_name="Southwark Park",
        day="Saturday",
        time="10:00",
        duration_hours=1,
        basket_url="https://clubspark.lta.org.uk/basket/abc123",
    )
    notifier.send_slot_found(slot)

    assert twilio_client.messages.create.call_count == len(RECIPIENTS)
    assert _tos(twilio_client) == [num for _, num in RECIPIENTS]
    bodies = _bodies(twilio_client)
    assert "Hey Alice!" in bodies[0]
    assert "Hey Bob!" in bodies[1]
    for body in bodies:
        assert "Southwark Park" in body
        assert "Saturday" in body
        assert "10AM-11AM" in body
        assert "https://clubspark.lta.org.uk/basket/abc123" in body


def test_nothing_available_sent_to_every_recipient(notifier, twilio_client):
    notifier.send_nothing_available()

    assert twilio_client.messages.create.call_count == len(RECIPIENTS)
    assert _tos(twilio_client) == [num for _, num in RECIPIENTS]
    for body in _bodies(twilio_client):
        assert body.strip() != ""


def test_from_number_is_taken_from_constructor(notifier, twilio_client):
    notifier.send_nothing_available()
    assert _froms(twilio_client) == [FROM] * len(RECIPIENTS)


def test_each_recipient_is_a_separate_api_call(notifier, twilio_client):
    notifier.send_slot_found(
        SlotFound(court_name="X", day="Sunday", time="11:00", duration_hours=1, basket_url="https://example")
    )
    notifier.send_nothing_available()

    assert twilio_client.messages.create.call_count == 2 * len(RECIPIENTS)
