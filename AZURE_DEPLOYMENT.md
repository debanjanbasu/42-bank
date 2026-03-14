# Azure Deployment Guide - 42-Bank

Complete guide for deploying 42-Bank to Azure AI Foundry with Cosmos DB.

## Quick Start

```bash
# 1. Deploy 42-Bank infrastructure (if not already deployed)
az deployment sub create --location eastus --template-file infra/main.bicep

# 2. Model Router is pre-deployed - no action needed
# Verify: az ai model-router show --name model-router --resource-group 42-bank

# 3. Seed database
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=...;AccountKey=..."
uv run python bootstrap.py
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
│  │       └─────────────┴─────────────┴─────────────┘                  │     │
│  │                           │                                         │     │
│ │ Model Router (dynamic routing) │ │
│  └───────────────────────────┼────────────────────────────────────────┘     │
│                              │ MCP Protocol                                 │
│  ┌───────────────────────────▼────────────────────────────────────────┐     │
│  │ 42-Bank Banking MCP Server (mcp_server.py)                         │     │
│  │                                                                     │     │
│  │  • check_balance  • send_money     • view_history                  │     │
│  │  • request_payment • approve_payment • list_products              │     │
│  │  • open_account   • list_pending_requests                         │     │
│  └───────────────────────────┬────────────────────────────────────────┘     │
│                              │ azure.cosmos.aio (async)                     │
│  ┌───────────────────────────▼────────────────────────────────────────┐     │
│  │ Azure Cosmos DB (Serverless)                                        │     │
│  │                                                                     │     │
│  │  users · change_feed · products · auth_devices                     │     │
│  │  key_backups · restore_challenges · token_blacklist                │     │
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
| [Docker Desktop](https://www.docker.com/products/docker-desktop) | Latest | Cosmos emulator (local dev) |

### Azure Resources

Ensure you have:
- Azure subscription with AI Foundry enabled
- Resource group `42-bank` in East US
- AI Foundry account and project `42-bank/42-bank`

---

## Step 1: Deploy 42-Bank Infrastructure

Deploy the 42-Bank specific resources (Cosmos DB, Log Analytics, Container Apps).

### 1.1 Using Bicep

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

### 1.2 Manual Deployment (Portal)

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

3. **Container App**
   - System-assigned managed identity
   - JWT_SECRET stored as encrypted Container Apps secret

---

## Step 2: Verify Pre-Deployed Model Router

> **Important**: The Model Router is already deployed and configured. Do not recreate it.

The Model Router provides a unified endpoint that dynamically routes requests to the best available model based on workload, cost, and performance characteristics.

### 2.1 Verify Model Router Exists

```bash
# Check if model router deployment exists
az ai model-router show \
  --name model-router \
  --resource-group 42-bank \
  --workspace-name 42-bank
```

### 2.2 Model Router Configuration (Pre-Configured)

The model router is pre-configured with the following routing strategy:

| Model | Active Params | Cost/Input | Cost/Output | Best For |
|-------|---------------|------------|-------------|----------|
| **Qwen3.5-35B-A3B** | 3B | ~$0.02/1M | ~$0.06/1M | **Default** - Cheapest MoE for banking |
| Qwen3.5-27B | 27B | ~$0.10/1M | ~$0.30/1M | Latency-sensitive queries |
| GPT-4o-mini | - | $0.15/1M | $0.60/1M | Complex reasoning |
| Qwen3.5-122B-A10B | 10B | ~$0.05/1M | ~$0.15/1M | High-capability tasks |

### 2.3 Model Router Benefits

- **Dynamic Load Balancing**: Automatically distributes requests across models
- **Cost Optimization**: Routes to most cost-effective model for each query type
- **Zero Downtime Updates**: Swap models without code changes
- **Failover**: Automatic retry on different model if one fails
- **Rate Limit Management**: Distributes load to avoid throttling

### 2.4 Testing Model Router Connectivity

```bash
# Test the pre-deployed endpoint
curl -X POST https://42-bank-us-east-2-resource.cognitiveservices.azure.com/openai/deployments/model-router/chat/completions \
  -H "Authorization: Bearer $AZURE_AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 10
  }'
```

---

## Step 3: Initialize Data

Seed the database with initial users and products.

### 3.1 Run Initialization Script

```bash
# Set connection string
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=...;AccountKey=..."

# Run initialization
uv run python bootstrap.py
```

### 3.2 Verify Data

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
docker-compose up -d

# Initialize database
uv run python bootstrap.py

# Run dev servers
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
- **A2A / MCP Logs**: Application Insights → Logs → traces

---

## Cost Management

### Estimated Monthly Costs

| Component | Tier | Cost |
|-----------|------|------|
| Cosmos DB | Serverless | $5-15 |
| Container Apps | Consumption | $0-10 |
| Model Router | Pay-per-use | $5-20 |
| Storage | LRS | $1-2 |
| **Total** | | **$11-47/month** |

### Cost Optimization Tips

1. **Use Serverless Cosmos DB** - No minimum spend
2. **Model Router** - Automatically routes to most cost-effective model
3. **Container Apps** - Scale to zero when idle
4. **Set Budget Alerts** - `az consumption budget create`

---

## Security

### Authentication

| Component | Method |
|-----------|--------|
| Container App → Cosmos DB | System-assigned managed identity + data-plane RBAC |
| Foundry Agents | Project Managed Identity |
| JWT_SECRET | Container Apps encrypted secret (passed as `@secure()` Bicep param at deploy time) |

### Network Security

- All endpoints HTTPS only (TLS terminated at Azure Front Door / App Service ingress)
- CORS configured for banking app
- Cosmos DB: Virtual network firewall

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

### Model Router Not Found

```bash
# Verify Model Router exists (should already be deployed)
az ai model-router show \
  --name model-router \
  --resource-group 42-bank \
  --workspace-name 42-bank

# If it doesn't exist, contact the infrastructure team - it should already be deployed
# Do NOT attempt to recreate it during application deployment
```

---

## Next Steps

1. ✅ Deploy 42-Bank infrastructure
2. ✅ Configure Model Router
3. ✅ Initialize database
4. ✅ Create Foundry agents
5. ✅ Test end-to-end flow
6. ✅ Configure monitoring

---

## Disaster Recovery

### RPO / RTO
- **RPO (Recovery Point Objective):** 15 minutes (Cosmos DB Continuous Backup)
- **RTO (Recovery Time Objective):** 1 hour

### Backup Configuration
Cosmos DB is configured with Continuous Backup mode. Backups are retained for 30 days.

### Restore Procedure
1. Navigate to Azure Portal → Cosmos DB account
2. Select **Point in Time Restore** under Backups
3. Choose target timestamp and resource group
4. Create restore target account
5. Update `AZURE_COSMOS_CONNECTION_STRING` in Container App env with new account endpoint
6. Restart Container Apps to pick up new connection string

### Monthly Restore Test
Run monthly to validate backup integrity:
```bash
# Restore to a test resource group
az cosmosdb restore \
  --account-name 42bank-cosmos-prod \
  --target-database-account-name 42bank-cosmos-restore-test \
  --restore-timestamp "$(date -u -v-7d '+%Y-%m-%dT%H:%M:%SZ')" \
  --resource-group 42-bank-rg-test \
  --location eastus
```

### Contact
For disaster recovery incidents, follow your organization's incident response playbook.

---

## References

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Cosmos DB Serverless](https://learn.microsoft.com/azure/cosmos-db/serverless)
- [Azure AI Model Router Documentation](https://learn.microsoft.com/azure/ai-foundry/model-router)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
