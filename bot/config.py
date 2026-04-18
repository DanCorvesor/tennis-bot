from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    lta_username: str
    lta_password: str
    clubspark_email: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    twilio_whatsapp_to: str
    whatsapp_allowlist: list[str]
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


def load_config(env_path: str | Path | None = None) -> Config:
    raise NotImplementedError
