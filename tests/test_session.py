from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bot.config import Config
from bot.session import BrowserSession, SessionExpiredError, SessionManager


def _config(tmp_path: Path) -> Config:
    return Config(
        lta_username="u",
        lta_password="p",
        clubspark_email="e@example.com",
        twilio_account_sid="AC",
        twilio_auth_token="tok",
        twilio_from="+1",
        sms_recipients=["+44"],
        courts=["https://clubspark.lta.org.uk/a"],
        preferred_times=["10:00"],
        booking_days=["Saturday"],
        slot_duration_hours=1,
        session_state_path=tmp_path / "state" / "session.json",
    )


@pytest.fixture
def fake_session():
    return BrowserSession(
        browser=MagicMock(name="browser"),
        context=MagicMock(name="context"),
        page=MagicMock(name="page"),
    )


@pytest.fixture
def factory(fake_session):
    return MagicMock(return_value=fake_session)


@pytest.fixture
def login_flow():
    return MagicMock()


def test_state_path_is_derived_from_config(tmp_path, factory, login_flow):
    cfg = _config(tmp_path)
    sm = SessionManager(cfg, browser_factory=factory, login_flow=login_flow)
    assert sm.state_path == cfg.session_state_path


def test_first_run_triggers_login(tmp_path, factory, login_flow, fake_session):
    cfg = _config(tmp_path)
    sm = SessionManager(cfg, browser_factory=factory, login_flow=login_flow)

    sm.launch()

    login_flow.assert_called_once_with(fake_session, cfg)
    factory.assert_called_once_with(None)
    fake_session.context.storage_state.assert_called_once()
    saved_path = fake_session.context.storage_state.call_args.kwargs["path"]
    assert Path(saved_path) == cfg.session_state_path


def test_existing_state_skips_login(tmp_path, factory, login_flow, fake_session):
    cfg = _config(tmp_path)
    cfg.session_state_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.session_state_path.write_text("{}")

    sm = SessionManager(cfg, browser_factory=factory, login_flow=login_flow)
    result = sm.launch()

    assert result is fake_session
    login_flow.assert_not_called()
    factory.assert_called_once_with(cfg.session_state_path)
    fake_session.context.storage_state.assert_not_called()


def test_expired_session_reauthenticates_once(tmp_path, factory, login_flow, fake_session):
    cfg = _config(tmp_path)
    sm = SessionManager(cfg, browser_factory=factory, login_flow=login_flow)

    sm.handle_expired(fake_session)

    login_flow.assert_called_once_with(fake_session, cfg)
    fake_session.context.storage_state.assert_called_once()


def test_second_expiry_raises(tmp_path, factory, login_flow, fake_session):
    cfg = _config(tmp_path)
    sm = SessionManager(cfg, browser_factory=factory, login_flow=login_flow)

    sm.handle_expired(fake_session)
    with pytest.raises(SessionExpiredError):
        sm.handle_expired(fake_session)

    assert login_flow.call_count == 1
