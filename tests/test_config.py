from pathlib import Path

import pytest

from bot.config import Config, ConfigError, load_config


VALID_ENV = """
LTA_USERNAME=DCORV97
LTA_PASSWORD=hunter2
CLUBSPARK_EMAIL=dan@example.com
NOTIFY_METHOD=twilio
TWILIO_ACCOUNT_SID=AC123
TWILIO_AUTH_TOKEN=tok456
TWILIO_FROM=+14155238886
SMS_RECIPIENTS=Alice:+447512211264,Bob:+447700900001
COURTS=https://clubspark.lta.org.uk/SouthwarkPark,https://clubspark.lta.org.uk/BrunswickPark,https://clubspark.lta.org.uk/BurgessParkSouthwark
PREFERRED_TIMES=10:00,11:00,09:00
BOOKING_DAYS=Saturday,Sunday
SLOT_DURATION_HOURS=1
""".strip()

VALID_NTFY_ENV = """
LTA_USERNAME=DCORV97
LTA_PASSWORD=hunter2
CLUBSPARK_EMAIL=dan@example.com
NOTIFY_METHOD=ntfy
NTFY_TOPIC=test-tennis
COURTS=https://clubspark.lta.org.uk/SouthwarkPark
PREFERRED_TIMES=10:00
BOOKING_DAYS=Saturday
SLOT_DURATION_HOURS=1
""".strip()


REQUIRED_FIELDS = [
    "LTA_USERNAME",
    "LTA_PASSWORD",
    "CLUBSPARK_EMAIL",
    "NOTIFY_METHOD",
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
    assert cfg.notify_method == "twilio"
    assert cfg.twilio_account_sid == "AC123"
    assert cfg.twilio_auth_token == "tok456"
    assert cfg.twilio_from == "+14155238886"


def test_ntfy_config(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text(VALID_NTFY_ENV)
    cfg = load_config(path)
    assert cfg.notify_method == "ntfy"
    assert cfg.ntfy_topic == "test-tennis"
    assert cfg.twilio_account_sid is None
    assert cfg.sms_recipients is None


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


def test_sms_recipients_is_list_of_name_number_tuples(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.sms_recipients == [("Alice", "+447512211264"), ("Bob", "+447700900001")]


def test_booking_days_is_list(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.booking_days == ["Saturday", "Sunday"]


def test_slot_duration_hours_is_int(env_file: Path):
    cfg = load_config(env_file)
    assert cfg.slot_duration_hours == 1
    assert isinstance(cfg.slot_duration_hours, int)


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_missing_required_field_raises(tmp_path: Path, missing: str):
    lines = [ln for ln in VALID_ENV.splitlines() if not ln.startswith(f"{missing}=")]
    env = tmp_path / ".env"
    env.write_text("\n".join(lines))

    with pytest.raises(ConfigError) as excinfo:
        load_config(env)
    assert missing in str(excinfo.value)
