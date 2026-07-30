"""Nodriver-backed browser session.

Playwright leaks automation signals at the CDP handshake (Runtime.enable /
Target.setAutoAttach) that Cloudflare detects regardless of fingerprint
patching. nodriver drives Chrome directly over the DevTools socket without
that middleware, so it clears Cloudflare's managed/Turnstile challenge where
Playwright cannot.

nodriver is async; this wraps it in a persistent event loop so the rest of the
(synchronous) bot can call it without caring. The session self-heals: it
cleans up orphaned Chrome before starting, and restarts a dead browser mid-run.
"""

import asyncio
import glob
import json
import logging
import os
import shutil
import subprocess
import time

log = logging.getLogger(__name__)


_FETCH_JS = """(async () => {
    const r = await fetch("%s", {headers: {"Accept": "application/json"}});
    return JSON.stringify({status: r.status, body: await r.text()});
})()"""

# Lean flags to keep a long-running Chrome's footprint down (it lives for days).
_CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",  # /dev/shm is tiny in Docker; avoid crashes
    "--disable-blink-features=AutomationControlled",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disk-cache-size=1",  # don't let the on-disk cache grow unbounded
    "--disable-crash-reporter",
]


def _free_mem_mb() -> str:
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable"):
                    return f"{int(line.split()[1]) // 1024} MB available"
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


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

    def _cleanup(self, wipe_profile: bool = False) -> None:
        """Kill orphaned Chrome and clear locks so a fresh launch can connect.
        Optionally wipe the whole profile (loses cf_clearance — last resort)."""
        subprocess.run(["pkill", "-9", "-f", "google-chrome"], check=False)
        time.sleep(1)
        if wipe_profile:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
            return
        for lock in glob.glob(f"{self._profile_dir}/Singleton*"):
            try:
                os.remove(lock)
            except OSError:
                pass

    def start(self) -> None:
        # nodriver waits only ~2.75s for Chrome to open its debug port; on a
        # loaded host Chrome can take longer, so retry. Clean up leftover Chrome
        # before the first attempt (the usual "worked then won't restart"
        # cause), and only wipe the profile as a last resort so cf_clearance
        # survives across restarts.
        attempts = 6
        for attempt in range(attempts):
            self._cleanup(wipe_profile=(attempt >= attempts - 2))
            try:
                self._run(self._start())
                log.info("Browser started (attempt %d)", attempt + 1)
                return
            except Exception as exc:  # noqa: BLE001
                msg = " ".join(str(exc).split())[:120]
                log.warning(
                    "Browser start attempt %d/%d failed: %s (mem: %s)",
                    attempt + 1, attempts, msg, _free_mem_mb(),
                )
                if attempt < attempts - 1:
                    time.sleep(3)
        raise RuntimeError(f"Browser failed to start after {attempts} attempts")

    async def _start(self) -> None:
        import nodriver as uc

        kwargs = dict(
            headless=self._headless,
            user_data_dir=self._profile_dir,
            sandbox=False,
            browser_args=list(_CHROME_ARGS),
        )
        if self._executable_path:
            kwargs["browser_executable_path"] = self._executable_path
        self._browser = await uc.start(**kwargs)

    def restart(self) -> None:
        log.warning("Restarting browser")
        self.stop()
        self._browser = None
        self._tab = None
        self.start()

    def clear_cloudflare(self, page_url: str) -> None:
        """Navigate to a page on the domain and wait for the Cloudflare
        challenge to resolve. Restarts the browser once if it has died."""
        try:
            self._run(self._clear_cloudflare(page_url))
        except _BrowserDead:
            self.restart()
            self._run(self._clear_cloudflare(page_url))

    async def _clear_cloudflare(self, page_url: str) -> None:
        try:
            self._tab = await self._browser.get(page_url)
        except Exception as exc:  # noqa: BLE001
            raise _BrowserDead(str(exc)) from exc
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


class _BrowserDead(Exception):
    """Raised when the browser connection is gone and needs a restart."""
