from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Config:
    lta_username: str
    lta_password: str
    clubspark_email: str
    notify_method: str
    courts: list[str]
    preferred_times: list[str]
    booking_days: list[str]
    slot_duration_hours: int
    release_hour: int
    session_state_path: Path
    ntfy_topic: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None
    sms_recipients: list[tuple[str, str]] | None = None
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
    "NOTIFY_METHOD",
    "COURTS",
    "PREFERRED_TIMES",
    "BOOKING_DAYS",
    "SLOT_DURATION_HOURS",
)

_TWILIO_REQUIRED = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM", "SMS_RECIPIENTS")
_NTFY_REQUIRED = ("NTFY_TOPIC",)


def _split(value: str) -> list[str]:
    return [p.strip() for p in value.split(",") if p.strip()]


def _parse_recipients(value: str) -> list[tuple[str, str]]:
    recipients = []
    for entry in _split(value):
        if ":" not in entry:
            raise ConfigError(
                f"SMS_RECIPIENTS entries must be Name:+number, got {entry!r}"
            )
        name, number = entry.split(":", 1)
        recipients.append((name.strip(), number.strip()))
    return recipients


def load_config(env_path: str | Path | None = None) -> Config:
    path = Path(env_path) if env_path else Path(".env")
    values = dotenv_values(path)

    missing = [k for k in _REQUIRED if not values.get(k)]
    if missing:
        raise ConfigError(
            f"Missing required .env variable(s): {', '.join(missing)}"
        )

    notify_method = values["NOTIFY_METHOD"]
    if notify_method == "twilio":
        extra_missing = [k for k in _TWILIO_REQUIRED if not values.get(k)]
        if extra_missing:
            raise ConfigError(
                f"NOTIFY_METHOD=twilio requires: {', '.join(extra_missing)}"
            )
    elif notify_method == "ntfy":
        extra_missing = [k for k in _NTFY_REQUIRED if not values.get(k)]
        if extra_missing:
            raise ConfigError(
                f"NOTIFY_METHOD=ntfy requires: {', '.join(extra_missing)}"
            )
    else:
        raise ConfigError(
            f"NOTIFY_METHOD must be 'twilio' or 'ntfy', got {notify_method!r}"
        )

    try:
        slot_hours = int(values["SLOT_DURATION_HOURS"])
    except ValueError as exc:
        raise ConfigError(
            f"SLOT_DURATION_HOURS must be an integer, got {values['SLOT_DURATION_HOURS']!r}"
        ) from exc

    release_hour = int(values.get("RELEASE_HOUR") or "20")
    session_state = values.get("SESSION_STATE_PATH") or ".state/session.json"

    sms_raw = values.get("SMS_RECIPIENTS")

    return Config(
        lta_username=values["LTA_USERNAME"],
        lta_password=values["LTA_PASSWORD"],
        clubspark_email=values["CLUBSPARK_EMAIL"],
        release_hour=release_hour,
        notify_method=notify_method,
        ntfy_topic=values.get("NTFY_TOPIC") or None,
        twilio_account_sid=values.get("TWILIO_ACCOUNT_SID") or None,
        twilio_auth_token=values.get("TWILIO_AUTH_TOKEN") or None,
        twilio_from=values.get("TWILIO_FROM") or None,
        sms_recipients=_parse_recipients(sms_raw) if sms_raw else None,
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
