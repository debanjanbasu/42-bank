# Azure Deployment Guide - 42-Bank

Complete guide for deploying 42-Bank to Azure AI Foundry with Cosmos DB.

## Quick Start

```bash
# 1. Deploy Cosmos DB MCP Toolkit (Microsoft Official)
git clone https://github.com/AzureCosmosDB/MCPToolKit.git
cd MCPToolKit
azd init
azd env set COSMOS_ENDPOINT "https://42bank-cosmos.documents.azure.com:443/"
azd env set AIF_PROJECT_ENDPOINT "https://42-bank.cognitiveservices.azure.com/"
azd up

# 2. Deploy 42-Bank infrastructure
cd ../42-bank
az deployment sub create --location eastus --template-file infra/main.bicep

# 3. Deploy Banking MCP Server
docker build -f Dockerfile.banking-mcp -t 42bank-banking-mcp .
az containerapp create --name 42bank-banking-mcp --image 42bank-banking-mcp
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Azure AI Foundry (42-bank/42-bank)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ Foundry Agent Service                                               │     │
│  │                                                                     │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │     │
│  │  │  Triage  │  │ Inquiry  │  │Transaction│ │ Advisor  │           │     │
│  │  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │           │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │     │
│  │       │             │             │             │                  │     │
│  │       └─────────────┴─────────────┴─────────────┘                  │     │
│  │                           │                                         │     │
│  │                  Qwen3.5-35B-A3B (MoE)                             │     │
│  │                  (3B active params)                                │     │
│  └───────────────────────────┼────────────────────────────────────────┘     │
│                              │ MCP Protocol                                 │
│  ┌───────────────────────────▼────────────────────────────────────────┐     │
│  │ 42-Bank Banking MCP Server (Container App)                          │     │
│  │                                                                     │     │
│  │  Banking Tools:                                                     │     │
│  │  • check_balance  • send_money     • view_history                  │     │
│  │  • request_payment • approve_payment • list_products              │     │
│  │  • open_account   • list_pending_requests                         │     │
│  └───────────────────────────┬────────────────────────────────────────┘     │
│                              │ HTTP                                          │
│  ┌───────────────────────────▼────────────────────────────────────────┐     │
│  │ Azure Cosmos DB MCP Toolkit (Microsoft Official)                   │     │
│  │                                                                     │     │
│  │  Generic Tools:                                                     │     │
│  │  • find_document_by_id  • get_recent_documents                     │     │
│  │  • text_search          • vector_search                            │     │
│  │  • get_approximate_schema                                         │     │
│  └───────────────────────────┬────────────────────────────────────────┘     │
│                              │                                               │
│  ┌───────────────────────────▼────────────────────────────────────────┐     │
│  │ Azure Cosmos DB (Serverless)                                        │     │
│  │                                                                     │     │
│  │  Containers:                                                        │     │
│  │  • users (partition: /token)                                        │     │
│  │  • transactions (partition: /timestamp)                            │     │
│  │  • pending_requests (partition: /request_id)                       │     │
│  │  • products (partition: /id)                                        │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) | 2.50+ | Azure resource management |
| [Bicep CLI](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install) | 0.22+ | Infrastructure as code |
| [Docker Desktop](https://www.docker.com/products/docker-desktop) | Latest | Container builds |
| [Azure Developer CLI](https://aka.ms/azure-dev/install) | 1.0+ | MCP Toolkit deployment |
| PowerShell | 7+ | Deployment scripts |

### Azure Resources

Ensure you have:
- Azure subscription with AI Foundry enabled
- Resource group `42-bank` in East US
- AI Foundry account and project `42-bank/42-bank`

---

## Step 1: Deploy Cosmos DB MCP Toolkit

The Microsoft official MCP Toolkit provides enterprise-grade Cosmos DB access.

### 1.1 Clone and Configure

```bash
git clone https://github.com/AzureCosmosDB/MCPToolKit.git
cd MCPToolKit

# Initialize
azd init

# Set environment
azd env set COSMOS_ENDPOINT "https://42bank-cosmos.documents.azure.com:443/"
azd env set AIF_PROJECT_ENDPOINT "https://42-bank.cognitiveservices.azure.com/"
azd env set EMBEDDING_DEPLOYMENT_NAME "text-embedding-ada-002"
```

### 1.2 Deploy Infrastructure

```bash
# Deploy all resources
azd up

# Deploy MCP server
.\scripts\Deploy-Cosmos-MCP-Toolkit.ps1 -ResourceGroup "42-bank"
```

### 1.3 Configure Foundry Integration

After deployment, the toolkit appears in Foundry catalog:

1. Navigate to Azure AI Foundry → 42-bank project
2. Go to **Build** → **Create agent**
3. Click **+ Add** in tools section
4. Select **Catalog** tab
5. Choose **Azure Cosmos DB**
6. Configure:
   - Authentication: **Project Managed Identity**
   - Audience: `<entra-app-client-id>` (from `deployment-info.json`)

---

## Step 2: Deploy 42-Bank Infrastructure

Deploy the 42-Bank specific resources (Cosmos DB, Key Vault, etc.).

### 2.1 Using Bicep

```bash
cd 42-bank

# Validate template
az deployment sub what-if \
  --location eastus \
  --template-file infra/main.bicep

# Deploy
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environment=production
```

### 2.2 Manual Deployment (Portal)

If you prefer the Azure portal:

1. **Cosmos DB Account**
   - Name: `42bank-cosmos`
   - API: NoSQL (Core)
   - Capacity mode: Serverless
   - Location: East US

2. **Database & Containers**
   - Database: `banking`
   - Containers:
     - `users` (partition: `/token`)
     - `transactions` (partition: `/timestamp`)
     - `pending_requests` (partition: `/request_id`)
     - `products` (partition: `/id`)

3. **Key Vault**
   - Name: `42bank-kv`
   - SKU: Standard
   - Enable RBAC

---

## Step 3: Deploy Qwen3.5-35B-A3B Model

Deploy the recommended MoE model for banking agents.

### 3.1 Via Azure AI Foundry Portal

1. Navigate to Models catalog
2. Search "Qwen3.5-35B-A3B"
3. Click **Deploy**
4. Select **Global Standard** deployment
5. Name: `qwen-35b-moe`

### 3.2 Model Selection Rationale

| Model | Active Params | Cost/Input | Cost/Output | Best For |
|-------|---------------|------------|-------------|----------|
| **Qwen3.5-35B-A3B** | 3B | ~$0.02/1M | ~$0.06/1M | **Recommended** - Cheapest MoE |
| Qwen3.5-27B | 27B | ~$0.10/1M | ~$0.30/1M | Latency-sensitive, best IFEval |
| GPT-4o-mini | - | $0.15/1M | $0.60/1M | OpenAI ecosystem |
| Qwen3.5-122B-A10B | 10B | ~$0.05/1M | ~$0.15/1M | Highest capability |

---

## Step 4: Deploy Banking MCP Server

Deploy the 42-Bank custom banking MCP server.

### 4.1 Build Container Image

```bash
# Build image
docker build -f Dockerfile.banking-mcp -t 42bank-banking-mcp .

# Test locally
docker run -p 8002:8002 \
  -e COSMOS_MCP_URL=https://cosmos-mcp.azurecontainerapps.io/mcp \
  -e COSMOS_DATABASE=banking \
  42bank-banking-mcp
```

### 4.2 Push to Azure Container Registry

```bash
# Get ACR name
ACR_NAME=$(az acr list --resource-group 42-bank --query "[0].name" -o tsv)

# Login
az acr login --name $ACR_NAME

# Tag and push
docker tag 42bank-banking-mcp ${ACR_NAME}.azurecr.io/42bank-banking-mcp:latest
docker push ${ACR_NAME}.azurecr.io/42bank-banking-mcp:latest
```

### 4.3 Deploy to Container Apps

```bash
# Create container app
az containerapp create \
  --name 42bank-banking-mcp \
  --resource-group 42-bank \
  --image ${ACR_NAME}.azurecr.io/42bank-banking-mcp:latest \
  --environment cosmos-mcp-env \
  --ingress external \
  --target-port 8002 \
  --env-vars \
    COSMOS_MCP_URL=https://cosmos-mcp.azurecontainerapps.io/mcp \
    COSMOS_DATABASE=banking
```

---

## Step 5: Initialize Data

Seed the database with initial users and products.

### 5.1 Run Initialization Script

```bash
# Set connection string
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=...;AccountKey=..."

# Run initialization
uv run python scripts/init-cosmos-local.py
```

### 5.2 Verify Data

```bash
# Via Azure Portal
# Navigate to Cosmos DB → Data Explorer → banking

# Via CLI
az cosmosdb sql query \
  --database-name banking \
  --container-name users \
  --query "SELECT * FROM c"
```

---

## Local Development

### Using Cosmos DB Emulator

```bash
# Start emulator
docker-compose up -d cosmos-emulator

# Wait for startup (30s)
sleep 30

# Initialize database
uv run python scripts/init-cosmos-local.py

# Run with Cosmos
DB_MODE=cosmos ./dev.sh alice
```

### Using SQLite (Default)

```bash
# No Docker required
./dev.sh alice
```

---

## Monitoring

### Application Insights

```bash
# View logs
az monitor app-insights logs-query \
  --app 42bank-insights \
  --analytics-query "traces | order by timestamp desc | limit 100"

# View metrics
az monitor app-insights metrics show \
  --app 42bank-insights \
  --metric "requests/duration"
```

### Dashboards

- **Azure Portal**: Resource Group → 42-bank → Application Insights
- **Cosmos DB**: Portal → 42bank-cosmos → Data Explorer
- **Container Apps**: Portal → 42bank-banking-mcp → Logs

---

## Cost Management

### Estimated Monthly Costs

| Component | Tier | Cost |
|-----------|------|------|
| Cosmos DB | Serverless | $5-15 |
| Container Apps | Consumption | $0-10 |
| Qwen3.5-35B | Pay-per-use | $5-20 |
| Key Vault | Standard | $0-1 |
| Storage | LRS | $1-2 |
| **Total** | | **$11-48/month** |

### Cost Optimization Tips

1. **Use Serverless Cosmos DB** - No minimum spend
2. **Qwen3.5-35B-A3B** - 3B active params = cheapest inference
3. **Container Apps** - Scale to zero when idle
4. **Set Budget Alerts** - `az consumption budget create`

---

## Security

### Authentication

| Component | Method |
|-----------|--------|
| MCP Toolkit | Entra ID + Managed Identity |
| Banking MCP | API Key + Entra ID |
| Cosmos DB | Key Vault secrets |
| Foundry Agents | Project Managed Identity |

### Network Security

- All endpoints HTTPS only
- CORS configured for banking app
- Cosmos DB: Virtual network firewall
- Key Vault: RBAC enabled

---

## Troubleshooting

### Cosmos Emulator Not Starting

```bash
# Check Docker
docker ps

# Restart emulator
docker-compose restart cosmos-emulator

# Check logs
docker-compose logs cosmos-emulator
```

### Model Not Found

```bash
# List deployments
az ml online-endpoint list \
  --resource-group 42-bank \
  --workspace-name 42-bank
```

### Container App Not Starting

```bash
# Check logs
az containerapp logs show \
  --name 42bank-banking-mcp \
  --resource-group 42-bank
```

---

## Next Steps

1. ✅ Deploy Cosmos DB MCP Toolkit
2. ✅ Deploy Qwen3.5-35B-A3B model
3. ✅ Deploy Banking MCP Server
4. ✅ Initialize database
5. ✅ Create Foundry agents
6. ✅ Test end-to-end flow
7. ✅ Configure monitoring

---

## References

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Cosmos DB MCP Toolkit](https://github.com/AzureCosmosDB/MCPToolKit)
- [Cosmos DB Serverless](https://learn.microsoft.com/azure/cosmos-db/serverless)
- [Qwen3.5 Model Card](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
