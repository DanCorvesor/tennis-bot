from pathlib import Path

import pytest

from bot.config import Config, ConfigError, load_config


VALID_ENV = """
LTA_USERNAME=DCORV97
LTA_PASSWORD=hunter2
CLUBSPARK_EMAIL=dan@example.com
TWILIO_ACCOUNT_SID=AC123
TWILIO_AUTH_TOKEN=tok456
TWILIO_FROM=+14155238886
SMS_RECIPIENTS=+447512211264,+447700900001
COURTS=https://clubspark.lta.org.uk/SouthwarkPark,https://clubspark.lta.org.uk/BrunswickPark,https://clubspark.lta.org.uk/BurgessParkSouthwark
PREFERRED_TIMES=10:00,11:00,09:00
BOOKING_DAYS=Saturday,Sunday
SLOT_DURATION_HOURS=1
SESSION_STATE_PATH=.state/session.json
""".strip()


REQUIRED_FIELDS = [
    "LTA_USERNAME",
    "LTA_PASSWORD",
    "CLUBSPARK_EMAIL",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM",
    "SMS_RECIPIENTS",
    "COURTS",
    "PREFERRED_TIMES",
    "BOOKING_DAYS",
    "SLOT_DURATION_HOURS",
]


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    path = tmp_path / ".env"
    path.write_text(VALID_ENV)
    return path


def test_load_config_returns_config_with_all_fields(env_file: Path):
    cfg = load_config(env_file)
    assert isinstance(cfg, Config)
    assert cfg.lta_username == "DCORV97"
    assert cfg.lta_password == "hunter2"
    assert cfg.clubspark_email == "dan@example.com"
    assert cfg.twilio_account_sid == "AC123"
    assert cfg.twilio_auth_token == "tok456"
    assert cfg.twilio_from == "+14155238886"


def test_preferred_times_is_ordered_list(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.preferred_times == ["10:00", "11:00", "09:00"]


def test_courts_is_list_of_urls(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.courts == [
        "https://clubspark.lta.org.uk/SouthwarkPark",
        "https://clubspark.lta.org.uk/BrunswickPark",
        "https://clubspark.lta.org.uk/BurgessParkSouthwark",
    ]


def test_sms_recipients_is_list_of_strings(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.sms_recipients == ["+447512211264", "+447700900001"]
    assert all(isinstance(n, str) for n in cfg.sms_recipients)


def test_booking_days_is_list(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.booking_days == ["Saturday", "Sunday"]


def test_slot_duration_hours_is_int(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.slot_duration_hours == 1
    assert isinstance(cfg.slot_duration_hours, int)


def test_card_fields_default_to_none(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.card_number is None
    assert cfg.card_expiry is None
    assert cfg.card_cvv is None
    assert cfg.card_name is None


def test_card_fields_loaded_when_present(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        VALID_ENV
        + "\nCARD_NUMBER=4111111111111111\nCARD_EXPIRY=12/30\nCARD_CVV=123\nCARD_NAME=Dan Corvesor\n"
    )
    cfg = load_config(env)
    assert cfg.card_number == "4111111111111111"
    assert cfg.card_expiry == "12/30"
    assert cfg.card_cvv == "123"
    assert cfg.card_name == "Dan Corvesor"


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_missing_required_field_raises(tmp_path: Path, missing: str):
    lines = [ln for ln in VALID_ENV.splitlines() if not ln.startswith(f"{missing}=")]
    env = tmp_path / ".env"
    env.write_text("\n".join(lines))

    with pytest.raises(ConfigError) as excinfo:
        load_config(env)
    assert missing in str(excinfo.value)
