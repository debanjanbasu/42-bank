# 42-Bank Single-Container Deployment
# AMD64 only for Azure deployment

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv venv /app/venv && \
    . /app/venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml

COPY . .
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh && mkdir -p /app/data/keys

ENV PATH="/app/venv/bin:$PATH"
ENV APP_ENV="production"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["/app/start.sh"]
