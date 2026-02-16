# 42 Bank: Azure AI Banking Agent Platform

42 Bank is a next-generation banking platform built with **Microsoft Agent Framework** and deployed on **Azure AI Foundry**. It features multi-agent orchestration, A2A/MCP protocol support, and post-quantum cryptographic security.

## Key Features

- **Azure AI Foundry Deployment**: Deploy directly as managed agents on Azure AI
- **Multi-Agent Orchestration**: 5 specialized agents collaborate autonomously  
- **A2A Protocol Support**: Expose agents via Agent-to-Agent protocol for external integration
- **MCP Server Support**: Banking tools accessible via Model Context Protocol
- **Post-Quantum Cryptography**: ML-DSA-44 (Dilithium) digital signatures
- **Phi-4 Mini Model**: Cost-efficient, high-performance AI model

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Azure AI Foundry                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         Hosted Agent (Primary Deployment)                  │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ BankingAgent (ChatAgent + 9 Banking Tools)           │  │ │
│  │  │  • check_balance    • send_money    • list_products  │  │ │
│  │  │  • view_history     • request_money • open_account   │  │ │
│  │  │  • list_accounts    • approve_payment                │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                          │                                  │ │
│  │  ┌───────────────────────▼──────────────────────────────┐  │ │
│  │  │ Hosting Adapter (Responses API)                      │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Phi-4-mini Model │ Azure Identity │ SQLite/Cosmos DB    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Secondary Integration Options:
┌──────────────┐              ┌──────────────┐
│ A2A Server   │              │ MCP Server   │
│ (Port 8000)  │              │ (Port 8001)  │
└──────────────┘              └──────────────┘
```

## Quick Start

### Prerequisites
- [uv](https://github.com/astral-sh/uv) - Python package manager
- [Foundry Local](https://learn.microsoft.com/azure/ai-foundry/foundry-local/get-started) - For local development
- [Docker](https://docs.docker.com/get-docker/) - For container builds

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

### Test Hosted Agent Locally

```bash
# Run the hosted agent on http://localhost:8088
uv run hosted_agent.py

# Test with curl
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "What is my checking balance?"}'
```

## Deploy to Azure AI Foundry

### Primary Deployment Method

Deploy the banking agent directly to Azure AI Foundry as a hosted agent:

```bash
# Build container for Azure AI Foundry (MUST be linux/amd64)
docker buildx build --platform linux/amd64 -t 42-bank-agent .

# Push to Azure Container Registry
az acr login --name <your-acr>
docker tag 42-bank-agent <your-acr>.azurecr.io/42-bank-agent:latest
docker push <your-acr>.azurecr.io/42-bank-agent:latest

# Deploy to Azure AI Foundry
# Configure in Azure portal or use SDK (see DEPLOYMENT.md)
```

> **Important**: Azure AI Foundry requires `linux/amd64` containers. On Apple Silicon, use `docker buildx` with the `--platform` flag.

### Alternative Deployment: Azure Developer CLI

```bash
# Initialize with Foundry starter template
azd init -t https://github.com/Azure-Samples/azd-ai-starter-basic

# Configure agent
azd ai agent init -m agent.yaml

# Deploy
azd up
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions and configuration options.

## Secondary Integration Options

### A2A Server (Agent-to-Agent Protocol)

For external agent integration via A2A protocol:

```bash
# Start A2A server (port 8000)
uv run main.py --a2a --user alice
```

The A2A server exposes banking agents with discovery, handoff, and streaming capabilities. See [DEPLOYMENT.md](DEPLOYMENT.md) for integration details.

### MCP Server (Model Context Protocol)

Expose banking tools via MCP for integration with MCP-compatible clients:

```bash
# HTTP mode (port 8001)
uv run main.py --mcp --user alice

# stdio mode (for Claude Desktop, etc.)
uv run main.py --mcp --stdio --user alice
```

See [DEVELOPER.md](DEVELOPER.md) for MCP client integration examples.

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
# Azure AI Foundry (Required for Production)
AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<name>
AZURE_AI_MODEL_DEPLOYMENT_NAME=Phi-4-mini

# Local Development
FOUNDRY_LOCAL_ENDPOINT=http://127.0.0.1:59402/v1
MODEL_NAME=Phi-4-mini-instruct-generic-gpu:5

# Banking Context
BANK_USER=alice
```

## Testing

```bash
uv run pytest
```

## License

MIT
