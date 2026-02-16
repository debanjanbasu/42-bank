# 42 Bank Hosted Agent - Dockerfile for Azure AI Foundry
# 
# IMPORTANT: Azure AI Foundry Hosted Agents ONLY support linux/amd64
# On Apple Silicon (ARM64) Macs, use buildx for cross-platform builds:
#   docker buildx build --platform linux/amd64 -t 42-bank-agent .
#
# For local testing on ARM64 Mac, run directly without Docker:
#   uv run hosted_agent.py

FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    agent-framework \
    azure-ai-agentserver-agentframework \
    azure-identity \
    python-dotenv \
    pqcrypto \
    pydantic \
    starlette \
    uvicorn

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/keys

# Expose port (hosting adapter uses 8088)
EXPOSE 8088

# Environment variables (configure in Foundry portal)
ENV AZURE_AI_PROJECT_ENDPOINT=""
ENV AZURE_AI_MODEL_DEPLOYMENT_NAME="Phi-4-mini"
ENV BANK_USER="alice"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8088/health || exit 1

# Run the hosted agent
CMD ["python", "hosted_agent.py"]
