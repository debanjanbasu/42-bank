# 42 Bank: A2A/MCP Compliant Quantum-Safe Agentic Platform

42 Bank is a next-generation banking prototype built with **Microsoft Agent Framework** and **Azure AI Foundry**. It features multi-agent orchestration, A2A/MCP protocol compliance, and post-quantum cryptographic security.

## Key Features

- **Azure AI Foundry Hosted Agents**: Deploy as managed containerized agents
- **A2A Protocol (v0.3.0)**: Expose agents via standardized Agent-to-Agent protocol
- **MCP (Model Context Protocol)**: Banking tools exposed as MCP resources
- **Multi-Agent Handoff**: 5 specialized agents collaborate autonomously
- **Post-Quantum Cryptography**: ML-DSA-44 (Dilithium) signatures

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Azure AI Foundry                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                Hosted Agent Container                       │ │
│  │  ┌────────────────────────────────────────────────────────┐│ │
│  │  │ BankingAgent (ChatAgent + 9 Tools)                     ││ │
│  │  │ - check_balance    - send_money    - list_products     ││ │
│  │  │ - view_history     - request_money - open_new_account  ││ │
│  │  │ - list_accounts    - approve_payment                    ││ │
│  │  └────────────────────────────────────────────────────────┘│ │
│  │                          │                                  │ │
│  │  ┌───────────────────────▼──────────────────────────────┐  │ │
│  │  │ Hosting Adapter (Responses API v1)                   │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Phi-4-mini Model │ Azure Identity │ SQLite/Cosmos DB    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Requirements
- [uv](https://github.com/astral-sh/uv)
- [Foundry Local](https://learn.microsoft.com/azure/ai-foundry/foundry-local/get-started)
- [Docker](https://docs.docker.com/get-docker/)

### Local Development

```bash
# Configure environment
cp .env.example .env

# Start Phi-4-mini locally
foundry model run Phi-4-mini-instruct-generic-gpu:5

# Initialize database and PQC keys
uv run bootstrap.py

# Test CLI chat
uv run main.py --user alice
```

### Local Agent Testing (Hosting Adapter)

```bash
# Test hosted agent locally on http://localhost:8088
uv run hosted_agent.py

# Test with curl
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "What is my checking balance?"}'
```

## Deployment to Azure AI Foundry

### Option 1: Azure Developer CLI (Recommended)

```bash
# Initialize with Foundry starter template
azd init -t https://github.com/Azure-Samples/azd-ai-starter-basic

# Configure agent
azd ai agent init -m agent.yaml

# Deploy
azd up
```

### Option 2: Manual Container Deployment

```bash
# Build container for Foundry (MUST be linux/amd64)
# On ARM64 Macs, use buildx for cross-platform build:
docker buildx build --platform linux/amd64 -t 42-bank-agent .

# Push to Azure Container Registry
az acr login --name <your-acr>
docker tag 42-bank-agent <your-acr>.azurecr.io/42-bank-agent:latest
docker push <your-acr>.azurecr.io/42-bank-agent:latest

# Create hosted agent via SDK
python scripts/create_hosted_agent.py
```

> **Note**: Azure AI Foundry Hosted Agents only support `linux/amd64`. On Apple Silicon Macs, run locally with `uv run hosted_agent.py` (no Docker needed for local testing).

### Option 3: A2A/MCP Endpoints (Azure Functions)

For external agent integration:

```bash
# A2A Server (port 8000)
uv run main.py --a2a --user alice

# MCP Server (port 8001)
uv run main.py --mcp --user alice
```

## Project Structure

```
├── hosted_agent.py      # Entry point for Foundry Hosted Agents
├── main.py              # CLI and A2A/MCP server modes
├── agents.py            # Handoff orchestration (5 agents)
├── a2a_server.py        # A2A protocol server
├── mcp_server.py        # MCP protocol server
├── tools.py             # PQC-signed banking tools (9 tools)
├── identity.py          # ML-DSA-44 key management
├── ledger.py            # SQLite document store
├── bank_agents/         # Modular agent definitions
├── Dockerfile           # Container for Hosted Agents
├── agent.yaml           # Agent definition for azd
└── host.json            # Azure Functions config
```

## Banking Tools

| Tool | Description |
|------|-------------|
| `check_balance` | View account balance |
| `view_history` | View transaction history |
| `list_my_accounts` | List all user accounts |
| `send_money` | Transfer funds to another user |
| `request_money` | Request payment from another user |
| `list_pending_requests` | List pending payment requests |
| `approve_payment` | Approve a payment request |
| `list_products` | List bank products (loans, cards) |
| `open_new_account` | Open a new account |

## Environment Variables

```env
# Required for Hosted Agents
AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<name>
AZURE_AI_MODEL_DEPLOYMENT_NAME=Phi-4-mini

# Local development
FOUNDRY_LOCAL_ENDPOINT=http://127.0.0.1:59402/v1
MODEL_NAME=Phi-4-mini-instruct-generic-gpu:5

# Banking user context
BANK_USER=alice
```

## Testing

```bash
uv run pytest
```

## License

MIT
