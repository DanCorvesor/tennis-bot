#!/bin/sh
set -e

# Start a virtual display so Chrome can run in true headful mode.
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:99

# exec so the Python process becomes PID 1 — signals and stdout/stderr
# propagate directly to Docker logs.
exec uv run python -m bot.scheduler
