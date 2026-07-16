FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Install Playwright's Chromium and its OS dependencies
RUN uv run playwright install --with-deps chromium

COPY bot/ bot/

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "python", "-m", "bot.scheduler"]
