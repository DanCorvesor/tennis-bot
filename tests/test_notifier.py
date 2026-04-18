from unittest.mock import MagicMock

import pytest

from bot.notifier import Notifier, SlotFound


FROM = "whatsapp:+14155238886"
RECIPIENTS = ["+447512211264", "+447700900001"]


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
        basket_url="https://clubspark.lta.org.uk/basket/abc123",
    )
    notifier.send_slot_found(slot)

    assert twilio_client.messages.create.call_count == len(RECIPIENTS)
    assert _tos(twilio_client) == [f"whatsapp:{n}" for n in RECIPIENTS]
    for body in _bodies(twilio_client):
        assert "Southwark Park" in body
        assert "Saturday" in body
        assert "10:00" in body
        assert "https://clubspark.lta.org.uk/basket/abc123" in body


def test_nothing_available_sent_to_every_recipient(notifier, twilio_client):
    notifier.send_nothing_available()

    assert twilio_client.messages.create.call_count == len(RECIPIENTS)
    assert _tos(twilio_client) == [f"whatsapp:{n}" for n in RECIPIENTS]
    for body in _bodies(twilio_client):
        assert body.strip() != ""


def test_error_message_includes_description(notifier, twilio_client):
    notifier.send_error("Login page timed out after 30s")

    assert twilio_client.messages.create.call_count == len(RECIPIENTS)
    assert _tos(twilio_client) == [f"whatsapp:{n}" for n in RECIPIENTS]
    for body in _bodies(twilio_client):
        assert "Login page timed out after 30s" in body


def test_from_number_is_taken_from_constructor(notifier, twilio_client):
    notifier.send_nothing_available()
    assert _froms(twilio_client) == [FROM] * len(RECIPIENTS)


def test_each_recipient_is_a_separate_api_call(notifier, twilio_client):
    notifier.send_slot_found(
        SlotFound(court_name="X", day="Sunday", time="11:00", basket_url="https://example")
    )
    notifier.send_nothing_available()
    notifier.send_error("boom")

    assert twilio_client.messages.create.call_count == 3 * len(RECIPIENTS)
