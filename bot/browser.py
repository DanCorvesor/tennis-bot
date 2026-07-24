"""Nodriver-backed browser session.

Playwright leaks automation signals at the CDP handshake (Runtime.enable /
Target.setAutoAttach) that Cloudflare detects regardless of fingerprint
patching. nodriver drives Chrome directly over the DevTools socket without
that middleware, so it clears Cloudflare's managed/Turnstile challenge where
Playwright cannot.

nodriver is async; this wraps it in a persistent event loop so the rest of the
(synchronous) bot can call it without caring.
"""

import asyncio
import json
import logging
import shutil

log = logging.getLogger(__name__)


_FETCH_JS = """(async () => {
    const r = await fetch("%s", {headers: {"Accept": "application/json"}});
    return JSON.stringify({status: r.status, body: await r.text()});
})()"""


class BrowserSession:
    def __init__(
        self,
        profile_dir: str,
        headless: bool = False,
        executable_path: str | None = None,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._profile_dir = profile_dir
        self._headless = headless
        self._executable_path = executable_path
        self._browser = None
        self._tab = None

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    def start(self) -> None:
        try:
            self._run(self._start())
        except Exception as exc:  # noqa: BLE001
            # A profile left by a different Chrome build (or a crash) can stop
            # Chrome starting. Wipe it and retry once from a clean profile.
            log.warning("Browser start failed (%s); wiping profile and retrying", exc)
            shutil.rmtree(self._profile_dir, ignore_errors=True)
            self._run(self._start())

    async def _start(self) -> None:
        import nodriver as uc

        browser_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",  # /dev/shm is tiny in Docker; avoid crashes
            "--disable-blink-features=AutomationControlled",
        ]
        kwargs = dict(
            headless=self._headless,
            user_data_dir=self._profile_dir,
            sandbox=False,
            browser_args=browser_args,
        )
        if self._executable_path:
            kwargs["browser_executable_path"] = self._executable_path
        self._browser = await uc.start(**kwargs)

    def clear_cloudflare(self, page_url: str) -> None:
        """Navigate to a page on the domain and wait for the Cloudflare
        challenge to resolve, establishing the cf_clearance cookie."""
        self._run(self._clear_cloudflare(page_url))

    async def _clear_cloudflare(self, page_url: str) -> None:
        self._tab = await self._browser.get(page_url)
        for i in range(40):
            await asyncio.sleep(1)
            title = str(await self._tab.evaluate("document.title") or "")
            if title and "Just a moment" not in title:
                return
            # Periodically attempt to click the interactive Turnstile checkbox
            # (nodriver locates it via OpenCV template matching). The passive
            # managed challenge clears on its own; this handles escalation.
            if i in (3, 8, 15, 25):
                try:
                    await self._tab.verify_cf()
                except Exception as exc:  # noqa: BLE001
                    log.debug("verify_cf attempt failed: %s", exc)
        raise RuntimeError("Cloudflare challenge did not clear")

    def fetch_json(self, api_url: str) -> dict:
        """Fetch a same-origin API URL from within the cleared page."""
        return self._run(self._fetch_json(api_url))

    async def _fetch_json(self, api_url: str) -> dict:
        if self._tab is None:
            raise RuntimeError("clear_cloudflare must be called first")
        raw = await self._tab.evaluate(_FETCH_JS % api_url, await_promise=True)
        result = json.loads(raw)
        if result["status"] != 200:
            raise RuntimeError(f"API returned HTTP {result['status']}")
        return json.loads(result["body"])

    def stop(self) -> None:
        if self._browser is not None:
            try:
                self._browser.stop()
            except Exception:  # noqa: BLE001
                pass
