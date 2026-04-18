from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from bot.config import Config


class SessionExpiredError(RuntimeError):
    """Raised when re-authentication also fails to restore a usable session."""


@dataclass
class BrowserSession:
    browser: object
    context: object
    page: object


BrowserFactory = Callable[[Path | None], BrowserSession]
LoginFlow = Callable[["BrowserSession", Config], None]


class SessionManager:
    def __init__(
        self,
        config: Config,
        browser_factory: BrowserFactory,
        login_flow: LoginFlow,
    ) -> None:
        self._config = config
        self._browser_factory = browser_factory
        self._login_flow = login_flow

    @property
    def state_path(self) -> Path:
        return self._config.session_state_path

    def launch(self) -> BrowserSession:
        raise NotImplementedError

    def handle_expired(self, session: BrowserSession) -> None:
        raise NotImplementedError
