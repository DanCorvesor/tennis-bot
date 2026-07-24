# NOTE: Real Google Chrome is required to clear Cloudflare — bundled Chromium
# is detected and blocked. Chrome for Linux is x86_64 only, so this image must
# be built and run on an amd64 host (not ARM).
FROM --platform=linux/amd64 python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Install real Google Chrome (channel "chrome") plus OS dependencies
RUN uv run playwright install --with-deps chrome

# Xvfb lets us run Chrome in true headful mode (headless is more likely to be
# escalated to an interactive Cloudflare challenge).
RUN apt-get update && \
    apt-get install -y --no-install-recommends xvfb xauth && \
    rm -rf /var/lib/apt/lists/*

COPY bot/ bot/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
