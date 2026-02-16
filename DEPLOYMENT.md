# Deployment Guide: Azure AI Foundry

This guide covers deploying 42 Bank to Azure AI Foundry.

## Overview

**Primary Deployment**: Deploy as a hosted agent directly on Azure AI Foundry  
**Secondary Options**: A2A/MCP servers for external agent integration

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Azure AI Foundry                              │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │             42 Bank Hosted Agent (Primary)                    │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ ChatAgent + 9 Banking Tools                             │ │  │
│  │  │ Exposed via Responses API                               │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                           │                                   │  │
│  │                           ▼                                   │  │
│  │  ┌──────────────────────────────────────────────────────┐   │  │
│  │  │ Phi-4-mini │ Azure Identity │ Storage                │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

External Integration Options:
┌─────────────────┐          ┌─────────────────┐
│ A2A Server      │          │ MCP Server      │
│ (Azure Function)│          │ (Azure Function)│
└─────────────────┘          └─────────────────┘
```

---

## Primary Deployment: Hosted Agent

Deploy 42 Bank directly to Azure AI Foundry as a containerized hosted agent.

## Primary Deployment: Hosted Agent

Deploy 42 Bank directly to Azure AI Foundry as a containerized hosted agent.

### Step 1: Build Container

```bash
# Build for Azure AI Foundry (MUST be linux/amd64)
docker buildx build --platform linux/amd64 -t 42-bank-agent .

# Test locally first
uv run hosted_agent.py
# Then test: curl -X POST http://localhost:8088/responses -H "Content-Type: application/json" -d '{"input": "Check balance"}'
```

### Step 2: Push to Azure Container Registry

```bash
# Login to your ACR
az acr login --name <your-acr-name>

# Tag and push
docker tag 42-bank-agent <your-acr-name>.azurecr.io/42-bank-agent:latest
docker push <your-acr-name>.azurecr.io/42-bank-agent:latest
```

### Step 3: Deploy to Azure AI Foundry

**Option A: Azure Portal**

1. Go to **Azure AI Foundry Portal** → Your Project
2. Navigate to **Agents** → **Create Agent**
3. Select **Container-based agent**
4. Configure:
   - **Container image**: `<your-acr>.azurecr.io/42-bank-agent:latest`
   - **Environment variables**:
     - `AZURE_AI_PROJECT_ENDPOINT`: Your project endpoint
     - `AZURE_AI_MODEL_DEPLOYMENT_NAME`: `Phi-4-mini`
     - `BANK_USER`: `alice`
5. Enable **Managed Identity** for Azure services access
6. Deploy

**Option B: Azure Developer CLI**

```bash
# Initialize with template
azd init -t https://github.com/Azure-Samples/azd-ai-starter-basic

# Configure agent
azd ai agent init -m agent.yaml

# Deploy
azd up
```

### Step 4: Test Deployed Agent

```bash
# Get agent endpoint from Azure portal
AGENT_ENDPOINT="https://<your-agent>.azurewebsites.net"

# Test
curl -X POST $AGENT_ENDPOINT/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(az account get-access-token --query accessToken -o tsv)" \
  -d '{"input": "What is my checking balance?"}'
```

### Environment Variables for Hosted Agent

Set these in Azure AI Foundry portal or Dockerfile:

```env
# Required
AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<name>
AZURE_AI_MODEL_DEPLOYMENT_NAME=Phi-4-mini
BANK_USER=alice

# Optional (defaults shown)
# Storage backend, managed identity, etc.
```

---

## Secondary Option: A2A Server Integration

Use when integrating with other Foundry agents via A2A protocol.

### Deploy A2A Server to Azure Functions

```bash
# Configure host for A2A
cp host.a2a.json host.json

# Deploy
func azure functionapp publish <your-function-app>
```

### Connect from Foundry Agent

1. Go to **Foundry Portal** → **Tools** → **Connect tool**
2. Select **Agent2Agent (A2A)**
3. Configure:
   - **Name**: `42-bank-a2a`
   - **Endpoint**: `https://<your-app>.azurewebsites.net/a2a/triage`
   - **Authentication**: Managed Identity or API key

### Use in Agent Code

### Use in Agent Code

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, A2ATool

with AIProjectClient(
    endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential()
) as project:
    a2a_connection = project.connections.get("42-bank-a2a")
    
    agent = project.agents.create_version(
        agent_name="BankingAssistant",
        definition=PromptAgentDefinition(
            model="Phi-4-mini",
            instructions="You are a banking assistant. Use A2A tool for banking operations.",
            tools=[A2ATool(project_connection_id=a2a_connection.id)],
        ),
    )
```

---

## Secondary Option: MCP Server Integration

Use when exposing banking tools via MCP for external clients.

### Deploy MCP Server

```bash
# Deploy as Azure Function
func azure functionapp publish <your-mcp-function-app>
```

### MCP Client Integration

**HTTP Mode:**
```bash
# Connect to MCP server
curl http://<your-app>.azurewebsites.net/tools
```

**stdio Mode (Claude Desktop, etc.):**
```json
{
  "mcpServers": {
    "42-bank": {
      "command": "python",
      "args": ["mcp_server.py", "alice", "--stdio"]
    }
  }
}
```

See [DEVELOPER.md](DEVELOPER.md) for detailed MCP integration examples.

---

## Model Configuration

### Deploy Phi-4-mini Model

In Azure AI Foundry portal:
1. Navigate to **Models** → **Deploy model**
2. Select **Phi-4-mini** from model catalog
3. Configure:
   - **Deployment name**: `Phi-4-mini`
   - **Instance type**: Choose based on load requirements
   - **Scale settings**: Configure auto-scaling

### Local Development

```bash
# Start Phi-4-mini locally with Foundry Local
foundry model run Phi-4-mini-instruct-generic-gpu:5
```

---

## Authentication & Security

### Managed Identity (Recommended)

Enable on your Azure resources:
```bash
az webapp identity assign --name <app-name> --resource-group <rg>
```

No secrets to manage - Azure handles authentication automatically.

### API Key (Simple)

For A2A/MCP servers:
```bash
# Set in Azure Function App Configuration
A2A_API_KEY=<your-secret-key>
```

### OAuth (Per-User)

For multi-user scenarios where each user accesses their own accounts:
1. Configure OAuth provider in Azure portal
2. Users consent on first use
3. Agent operates with user's permissions

---

## Production Checklist

- [ ] Deploy Phi-4-mini model in Azure AI Foundry
- [ ] Build and push container to ACR (linux/amd64)
- [ ] Deploy hosted agent with managed identity
- [ ] Configure environment variables
- [ ] Set up Application Insights for monitoring
- [ ] Configure Cosmos DB for production storage (optional)
- [ ] Enable auto-scaling based on load
- [ ] Set up CI/CD pipeline
- [ ] Test agent endpoints
- [ ] Configure CORS if needed

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Container fails to start | Check logs in Azure portal. Verify environment variables are set |
| Authentication errors | Ensure managed identity is enabled and has correct permissions |
| Model not found | Deploy Phi-4-mini model in Azure AI Foundry project |
| Slow responses | Check model instance type and auto-scaling settings |
| Database errors | Run bootstrap.py to initialize database, or configure Cosmos DB |

---

## Related Documentation

- [Azure AI Foundry Hosted Agents](https://learn.microsoft.com/azure/ai-foundry/agents)
- [A2A Protocol](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/agent-to-agent)
- [MCP on Azure Functions](https://learn.microsoft.com/azure/azure-functions/self-hosted-mcp-servers)
- [Phi-4 Mini Model](https://learn.microsoft.com/azure/ai-foundry/models/phi-4)
