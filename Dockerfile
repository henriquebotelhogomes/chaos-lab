# ==========================================
# Stage 1: Python Dependencies with uv
# ==========================================
FROM python:3.12-slim AS builder
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install uv for blazing-fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy pyproject.toml, README.md, and source code
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN uv pip install --system --no-cache -e .

# ==========================================
# Stage 2: Final Production Runtime (Scale-to-Zero)
# ==========================================
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST="0.0.0.0"

# Security: Create non-root user
RUN addgroup --system --gid 1001 chaosgroup && \
    adduser --system --uid 1001 --gid 1001 chaosuser

# Copy installed packages and application binaries
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=chaosuser:chaosgroup src/ /app/src/

USER chaosuser

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]

