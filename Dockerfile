# 42-Bank Single-Container Deployment (Multi-stage, minimal)
# AMD64 for Azure deployment

# ---- Build stage ----
FROM python:3.14-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv venv /build/venv && \
    . /build/venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml

# ---- Runtime stage ----
FROM python:3.14-slim

WORKDIR /app

# Only curl needed at runtime (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy venv from builder (contains all Python deps, no gcc/uv)
COPY --from=builder /build/venv /app/venv

# Copy application code
COPY . .
RUN chmod +x /app/start.sh && mkdir -p /app/data/keys

ENV PATH="/app/venv/bin:$PATH"
ENV APP_ENV="production"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["/app/start.sh"]
