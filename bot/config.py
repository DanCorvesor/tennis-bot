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
    schedule: list[tuple[list[str], list[str]]]
    slot_duration_hours: int
    release_hour: int
    ntfy_topic: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None
    sms_recipients: list[tuple[str, str]] | None = None


class ConfigError(ValueError):
    """Raised when .env is missing a required value."""


_REQUIRED = (
    "LTA_USERNAME",
    "LTA_PASSWORD",
    "CLUBSPARK_EMAIL",
    "NOTIFY_METHOD",
    "COURTS",
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


def _parse_schedule(value: str) -> list[tuple[list[str], list[str]]]:
    """Parse BOOKING_SCHEDULE into groups of (days, times).

    Format: "Days=times;Days=times;..."
    Example: "Saturday,Sunday=10:00,11:00;Monday,Tuesday=18:00,19:00"
    """
    groups: list[tuple[list[str], list[str]]] = []
    for group in value.split(";"):
        group = group.strip()
        if not group:
            continue
        if "=" not in group:
            raise ConfigError(
                f"BOOKING_SCHEDULE entries must be Days=times, got {group!r}"
            )
        days_part, times_part = group.split("=", 1)
        days = _split(days_part)
        times = _split(times_part)
        if not days or not times:
            raise ConfigError(
                f"BOOKING_SCHEDULE entry has empty days or times: {group!r}"
            )
        groups.append((days, times))
    return groups


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
    sms_raw = values.get("SMS_RECIPIENTS")

    if values.get("BOOKING_SCHEDULE"):
        schedule = _parse_schedule(values["BOOKING_SCHEDULE"])
    elif values.get("BOOKING_DAYS") and values.get("PREFERRED_TIMES"):
        schedule = [(_split(values["BOOKING_DAYS"]), _split(values["PREFERRED_TIMES"]))]
    else:
        raise ConfigError(
            "Set BOOKING_SCHEDULE or both BOOKING_DAYS and PREFERRED_TIMES"
        )

    return Config(
        lta_username=values["LTA_USERNAME"],
        lta_password=values["LTA_PASSWORD"],
        clubspark_email=values["CLUBSPARK_EMAIL"],
        notify_method=notify_method,
        release_hour=release_hour,
        ntfy_topic=values.get("NTFY_TOPIC") or None,
        twilio_account_sid=values.get("TWILIO_ACCOUNT_SID") or None,
        twilio_auth_token=values.get("TWILIO_AUTH_TOKEN") or None,
        twilio_from=values.get("TWILIO_FROM") or None,
        sms_recipients=_parse_recipients(sms_raw) if sms_raw else None,
        courts=_split(values["COURTS"]),
        schedule=schedule,
        slot_duration_hours=slot_hours,
    )
