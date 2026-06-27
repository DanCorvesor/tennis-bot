from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Config:
    lta_username: str
    lta_password: str
    clubspark_email: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from: str
    twilio_to: str
    sms_recipients: list[str]
    courts: list[str]
    preferred_times: list[str]
    booking_days: list[str]
    slot_duration_hours: int
    session_state_path: Path
    card_number: str | None = None
    card_expiry: str | None = None
    card_cvv: str | None = None
    card_name: str | None = None


class ConfigError(ValueError):
    """Raised when .env is missing a required value."""


_REQUIRED = (
    "LTA_USERNAME",
    "LTA_PASSWORD",
    "CLUBSPARK_EMAIL",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM",
    "TWILIO_TO",
    "SMS_RECIPIENTS",
    "COURTS",
    "PREFERRED_TIMES",
    "BOOKING_DAYS",
    "SLOT_DURATION_HOURS",
)


def _split(value: str) -> list[str]:
    return [p.strip() for p in value.split(",") if p.strip()]


def load_config(env_path: str | Path | None = None) -> Config:
    path = Path(env_path) if env_path else Path(".env")
    values = dotenv_values(path)

    missing = [k for k in _REQUIRED if not values.get(k)]
    if missing:
        raise ConfigError(
            f"Missing required .env variable(s): {', '.join(missing)}"
        )

    try:
        slot_hours = int(values["SLOT_DURATION_HOURS"])
    except ValueError as exc:
        raise ConfigError(
            f"SLOT_DURATION_HOURS must be an integer, got {values['SLOT_DURATION_HOURS']!r}"
        ) from exc

    session_state = values.get("SESSION_STATE_PATH") or ".state/session.json"

    return Config(
        lta_username=values["LTA_USERNAME"],
        lta_password=values["LTA_PASSWORD"],
        clubspark_email=values["CLUBSPARK_EMAIL"],
        twilio_account_sid=values["TWILIO_ACCOUNT_SID"],
        twilio_auth_token=values["TWILIO_AUTH_TOKEN"],
        twilio_from=values["TWILIO_FROM"],
        twilio_to=values["TWILIO_TO"],
        sms_recipients=_split(values["SMS_RECIPIENTS"]),
        courts=_split(values["COURTS"]),
        preferred_times=_split(values["PREFERRED_TIMES"]),
        booking_days=_split(values["BOOKING_DAYS"]),
        slot_duration_hours=slot_hours,
        session_state_path=Path(session_state),
        card_number=values.get("CARD_NUMBER") or None,
        card_expiry=values.get("CARD_EXPIRY") or None,
        card_cvv=values.get("CARD_CVV") or None,
        card_name=values.get("CARD_NAME") or None,
    )
