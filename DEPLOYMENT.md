# Deployment Guide: Azure AI Foundry

This guide covers deploying 42 Bank agents to Azure AI Foundry using A2A and MCP protocols.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Azure AI Foundry                              │
│  ┌────────────────┐                    ┌────────────────────────┐  │
│  │ Foundry Agent  │                    │  Foundry Agent         │  │
│  │ (with A2ATool) │                    │  (with MCP Tool)       │  │
│  └───────┬────────┘                    └───────────┬────────────┘  │
│          │ A2A Protocol                            │ MCP Protocol   │
│          ▼                                         ▼                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              42 Bank Services (Azure Functions)               │  │
│  │  ┌─────────────────┐           ┌─────────────────────────┐   │  │
│  │  │ A2A Server      │           │ MCP Server              │   │  │
│  │  │ :8000           │           │ :8001                   │   │  │
│  │  │ /a2a/{agent}    │           │ /sse, /messages         │   │  │
│  │  └────────┬────────┘           └────────────┬────────────┘   │  │
│  │           │                                  │                │  │
│  │           ▼                                  ▼                │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │ SQLite/Cosmos DB │ Identity (ML-DSA-44)             │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Option 1: A2A Endpoint for Foundry Agents

Your A2A server becomes an endpoint that Foundry agents can call using `A2ATool`.

### Step 1: Deploy A2A Server to Azure Functions

```bash
# Use A2A host configuration
cp host.a2a.json host.json

# Deploy
func azure functionapp publish <your-function-app>
```

### Step 2: Create A2A Connection in Foundry Portal

1. Go to **Foundry Portal** → **Tools** → **Connect tool**
2. Select **Custom** → **Agent2Agent (A2A)**
3. Configure:
   - **Name**: `42-bank-agents`
   - **A2A Agent Endpoint**: `https://<your-app>.azurewebsites.net/a2a/triage`
   - **Authentication**: 
     - Key-based: Set `x-api-key` header with your API key
     - Or Microsoft Entra ID (Managed Identity)

### Step 3: Create Foundry Agent with A2ATool

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, A2ATool

with AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential()
) as project:
    # Get the A2A connection
    a2a_connection = project.connections.get("42-bank-agents")
    
    # Create agent with A2A tool
    agent = project.agents.create_version(
        agent_name="BankingAssistant",
        definition=PromptAgentDefinition(
            model=os.environ["FOUNDRY_MODEL_DEPLOYMENT_NAME"],
            instructions="You are a banking assistant. Use the A2A tool to handle banking queries.",
            tools=[A2ATool(project_connection_id=a2a_connection.id)],
        ),
    )
    
    print(f"Agent created: {agent.name} v{agent.version}")
```

### Environment Variables

```env
FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.api.azureml.ms
FOUNDRY_MODEL_DEPLOYMENT_NAME=Phi-4-mini
A2A_PROJECT_CONNECTION_NAME=42-bank-agents
```

---

## Option 2: MCP Server for Tool Integration

Expose banking tools via MCP for Foundry agents to use directly.

### Step 1: Deploy MCP Server

```bash
# Use MCP host configuration  
cp host.json host.json.backup
# host.json is already configured for MCP stdio mode

func azure functionapp publish <your-function-app>
```

### Step 2: Configure MCP in Foundry

Add the MCP server connection in Foundry portal:
1. **Tools** → **Connect tool** → **MCP**
2. Point to your Function App endpoint

### MCP Tools Available

| Tool | Description |
|------|-------------|
| `check_balance` | View account balance |
| `view_history` | View transaction history |
| `send_money` | Transfer funds to another user |
| `request_money` | Request payment |
| `approve_payment` | Approve pending requests |
| `list_products` | List bank products |
| `open_new_account` | Open new account |

---

## Authentication

### Key-Based (Simple)

```bash
# Set API key when starting server
A2A_API_KEY=your-secret-key python main.py --a2a --require-auth
```

Configure in Foundry connection:
- **Credential name**: `x-api-key`
- **Credential value**: `<your-secret-key>`

### Microsoft Entra ID (Recommended for Production)

1. Enable Managed Identity on your Function App
2. Configure A2A connection with **Agent Identity** or **Project Managed Identity**
3. No secrets to manage - Azure handles token acquisition

### OAuth Identity Passthrough

For per-user authentication (each user accesses their own accounts):
1. Configure OAuth in Foundry portal
2. Users consent on first interaction
3. Agent acts on behalf of each user

---

## Model Configuration

### Local Development (Foundry Local)

```bash
foundry model run Phi-4-mini-instruct-generic-gpu:5
```

### Azure AI Foundry (Hosted)

Deploy **Phi-4-mini** model in your Foundry project:
- Cost-efficient for banking tasks
- Good balance of performance and latency

```env
AZURE_AI_MODEL_DEPLOYMENT_NAME=Phi-4-mini
```

---

## Production Checklist

- [ ] Deploy to Azure Functions Flex Consumption plan
- [ ] Enable Managed Identity authentication
- [ ] Configure Cosmos DB for production storage
- [ ] Set up Application Insights for monitoring
- [ ] Enable Change Feed for audit logging
- [ ] Configure CORS for your client applications
- [ ] Set up API rate limiting

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| 401 Unauthorized | Check API key or Managed Identity configuration |
| Connection not found | Verify `A2A_PROJECT_CONNECTION_NAME` matches portal |
| Agent doesn't invoke tool | Ensure prompt requires the remote agent |
| Timeout errors | Increase timeout in connection settings |

---

## Related Documentation

- [A2A Tool in Foundry](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/agent-to-agent)
- [A2A Authentication](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/agent-to-agent-authentication)
- [MCP Servers on Azure Functions](https://learn.microsoft.com/azure/azure-functions/self-hosted-mcp-servers)
