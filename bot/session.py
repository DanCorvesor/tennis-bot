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
        self._reauthenticated = False

    @property
    def state_path(self) -> Path:
        return self._config.session_state_path

    def launch(self) -> BrowserSession:
        if self.state_path.exists():
            return self._browser_factory(self.state_path)

        session = self._browser_factory(None)
        self._login_flow(session, self._config)
        self._save_state(session)
        return session

    def handle_expired(self, session: BrowserSession) -> None:
        if self._reauthenticated:
            raise SessionExpiredError(
                "Session expired after re-authenticating once; aborting."
            )
        self._reauthenticated = True
        self._login_flow(session, self._config)
        self._save_state(session)

    def _save_state(self, session: BrowserSession) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        session.context.storage_state(path=str(self.state_path))


def playwright_browser_factory(playwright, headless: bool = True) -> BrowserFactory:
    def factory(storage_state: Path | None) -> BrowserSession:
        browser = playwright.firefox.launch(headless=headless)
        context = browser.new_context(
            storage_state=str(storage_state) if storage_state else None,
        )
        page = context.new_page()
        return BrowserSession(browser=browser, context=context, page=page)

    return factory


def clubspark_login(session: BrowserSession, config: Config) -> None:
    page = session.page
    page.goto("https://clubspark.lta.org.uk/SouthwarkPark/Booking", wait_until="domcontentloaded")
    page.get_by_test_id("sign-in-link").wait_for(timeout=30_000)
    accept_btn = page.get_by_role("button", name="Accept All")
    if accept_btn.is_visible():
        accept_btn.click()
    page.get_by_test_id("sign-in-link").click()
    page.locator('button[value="LTA2"]').click()
    page.get_by_role("textbox", name="Username").fill(config.lta_username)
    page.get_by_placeholder("Password").fill(config.lta_password)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url("**/clubspark.lta.org.uk/**", timeout=30_000)
