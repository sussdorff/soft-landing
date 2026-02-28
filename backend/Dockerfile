# syntax=docker/dockerfile:1
# Backend Dockerfile — multi-stage build with uv for fast, reproducible installs

# ---------- Stage 1: build ----------
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS build

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy app code and install the project itself
COPY app/ app/

# ---------- Stage 2: runtime ----------
FROM python:3.14-slim-bookworm

WORKDIR /app

# Copy the virtual environment from the build stage
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/app app/

# Put the venv on PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
