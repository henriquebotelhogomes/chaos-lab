# ==========================================
# Multi-Stage Dockerfile for Chaos Lab
# Optimized for Google Cloud Run (Scale-to-Zero)
# ==========================================

FROM ghcr.io/astral-sh/uv:0.5.21 AS uv_bin
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv_bin /uv /uvx /bin/

# Install dependencies using uv
COPY pyproject.toml .
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml

# ==========================================
# Final Runtime Stage (Non-Root User)
# ==========================================
FROM python:3.12-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

# Security: Create and run as non-root user
RUN groupadd -g 10001 appuser && \
    useradd -u 10000 -g appuser -s /bin/bash -m appuser

# Copy virtualenv and application code
COPY --from=builder /opt/venv /opt/venv
COPY src /app/src

USER appuser

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
