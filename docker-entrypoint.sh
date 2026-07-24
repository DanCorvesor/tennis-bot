#!/bin/sh
set -e

# Start a virtual display so Chrome can run in true headful mode.
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:99

# The profile lives on a persistent volume. An unclean shutdown leaves Chrome
# singleton lock files behind; because the container's hostname changes on
# recreate, Chrome then thinks the profile is in use "on another computer" and
# refuses to launch. Clear the stale locks before starting.
PROFILE_DIR="${BROWSER_PROFILE_DIR:-/app/.state/chrome-profile}"
rm -f "$PROFILE_DIR"/Singleton* 2>/dev/null || true

# exec so the Python process becomes PID 1 — signals and stdout/stderr
# propagate directly to Docker logs.
exec uv run python -m bot.scheduler
