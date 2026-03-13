# 42 Bank Hosted Agent - Dockerfile for Azure AI Foundry
# 
# IMPORTANT: Azure AI Foundry Hosted Agents ONLY support linux/amd64
# On Apple Silicon (ARM64) Macs, use buildx for cross-platform builds:
#   docker buildx build --platform linux/amd64 -t 42-bank-agent .

FROM --platform=linux/amd64 python:3.12-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files for caching
COPY pyproject.toml uv.lock ./

# Install dependencies directly to the system (optimal for containers)
# Using --system to avoid the overhead of a virtualenv inside the container
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/keys

# Expose port (A2A server uses 8000 by default)
EXPOSE 8000

# Environment variables
ENV APP_ENV="production"
ENV BANK_USER="alice"
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the A2A server
CMD ["python", "a2a_server.py", "--port", "8000"]
