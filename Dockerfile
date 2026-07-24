# NOTE: Real Google Chrome is required to clear Cloudflare — bundled Chromium
# is detected and blocked. Chrome for Linux is x86_64 only, so this image must
# be built and run on an amd64 host (not ARM).
FROM --platform=linux/amd64 python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Install real Google Chrome, plus Xvfb (nodriver drives Chrome headful under a
# virtual display) and xauth (needed by X).
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget gnupg ca-certificates && \
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y --no-install-recommends /tmp/chrome.deb xvfb xauth && \
    rm -f /tmp/chrome.deb && \
    rm -rf /var/lib/apt/lists/*

ENV BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

COPY bot/ bot/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
