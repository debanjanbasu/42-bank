# Production Release Guide - 42-Bank

This guide covers the production deployment of 42-Bank using the pre-deployed Model Router.

## Model Router Overview

The production deployment uses the **pre-deployed Azure AI Model Router** at:
```
https://42-bank-us-east-2-resource.cognitiveservices.azure.com/openai/deployments/model-router/chat/completions?api-version=2024-05-01-preview
```

### Benefits

1. **Dynamic Model Routing**: Automatically routes requests to the best available model based on:
   - Query complexity
   - Latency requirements
   - Cost optimization
   - Model availability

2. **Zero-Downtime Model Updates**: Swap underlying models without code changes

3. **Load Balancing**: Distributes requests across multiple model instances

4. **Failover**: Automatic retry on alternative models if primary fails

5. **Cost Optimization**: Routes to most cost-effective model for each query type

### Important: Pre-Deployed Model Router

> **The Model Router is already deployed and configured.** Do not attempt to create or modify the Model Router during deployment. Simply configure your application to use the existing endpoint.

**Environment Configuration:**
```bash
AZURE_AI_PROJECT_ENDPOINT=https://42-bank-us-east-2-resource.cognitiveservices.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME=model-router
```

---

## Pre-Deployment Checklist

### 1. Infrastructure Setup (Pre-Deployed Resources)

> **Note**: The following resources are already deployed. Verify they exist but do not recreate:

- [x] Azure Resource Group (`42-bank`)
- [x] Azure AI Foundry project configured
- [x] **Model Router endpoint** (pre-deployed, do not modify)
- [ ] Cosmos DB account created (Serverless mode)
- [ ] Container Apps environment configured
- [ ] Application Insights enabled
- [ ] Managed Identity configured for Container Apps

### 3. Database Setup

- [ ] Cosmos DB containers created:
  - [ ] `users` (partition: `/token`)
  - [ ] `transactions` (partition: `/timestamp`)
  - [ ] `pending_requests` (partition: `/request_id`)
  - [ ] `products` (partition: `/id`)
  - [ ] `change_feed` (partition: `/event_type`)
  - [ ] `auth_devices` (partition: `/user_token`)
  - [ ] `key_backups` (partition: `/user_token`)
  - [ ] `restore_challenges` (partition: `/backup_id`)
  - [ ] `token_blacklist` (partition: `/jti`)
- [ ] Initial data seeded
- [ ] Backup/restore tested

### 4. Security Configuration

- [ ] JWT secret generated and stored as Container Apps encrypted secret
- [ ] Managed Identity granted "Cosmos DB Built-in Data Contributor"
- [ ] CORS configured for mobile app domains
- [ ] TLS/HTTPS enforced
- [ ] Rate limiting enabled

---

## Deployment Steps

### Step 1: Deploy Infrastructure (One-Time Only)

> **Important**: The Model Router is pre-deployed. Do not run this step if infrastructure already exists. Only deploy if this is a fresh environment:

```bash
# Navigate to infrastructure directory
cd infra

# Deploy Bicep template (ONLY if infrastructure doesn't exist)
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters \
    environment=production \
    jwtSecret=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
```

### Step 2: Verify Pre-Deployed Model Router

> **DO NOT recreate the Model Router**. It is already deployed and configured.

1. **Verify Model Router exists**:
   ```bash
   # Check if model router deployment exists
   az ai model-router show \
     --name model-router \
     --resource-group 42-bank \
     --workspace-name 42-bank
   ```

2. **Verify endpoint is accessible**:
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

3. **If Model Router doesn't exist**: Contact the infrastructure team - it should already be deployed.

### Step 3: Deploy Application

```bash
# Build container image
docker build -t 42bank:latest .

# Push to Azure Container Registry
az acr login --name 42bankregistry
docker tag 42bank:latest 42bankregistry.azurecr.io/42bank:latest
docker push 42bankregistry.azurecr.io/42bank:latest

# Update Container App
az containerapp update \
  --name 42bank-api \
  --resource-group 42-bank \
  --image 42bankregistry.azurecr.io/42bank:latest
```

### Step 4: Initialize Database

```bash
# Set connection string (from Container App environment)
export COSMOS_ENDPOINT=$(az containerapp show \
  --name 42bank-api \
  --resource-group 42-bank \
  --query "environmentVariables[?name=='COSMOS_ENDPOINT'].value" -o tsv)

# Run bootstrap script
uv run python bootstrap.py
```

### Step 5: Verify Deployment

```bash
# Check Container App health
az containerapp show \
  --name 42bank-api \
  --resource-group 42-bank \
  --query "properties.latestRevisionName"

# Test API endpoint
curl -X GET https://42bank-api.azurecontainerapps.io/health

# Test Model Router connectivity
curl -X POST https://42-bank-us-east-2-resource.cognitiveservices.azure.com/openai/deployments/model-router/chat/completions \
  -H "Authorization: Bearer $AZURE_AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 10
  }'
```

---

## Environment Variables (Production)

| Variable | Value | Description |
|----------|-------|-------------|
| `COSMOS_ENDPOINT` | `https://42bank-cosmos.documents.azure.com:443/` | Cosmos DB endpoint (managed identity) |
| `COSMOS_DATABASE` | `banking` | Database name |
| `AZURE_AI_PROJECT_ENDPOINT` | `https://42-bank-us-east-2-resource.cognitiveservices.azure.com/` | Model router endpoint |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | `model-router` | Model deployment name |
| `APP_ENV` | `production` | Environment name |
| `JWT_SECRET` | `<encrypted>` | Stored as Container Apps secret |
| `JWT_EXPIRY_HOURS` | `168` | Token expiry (7 days) |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Monitoring & Observability

### Application Insights

```bash
# View live metrics
az monitor app-insights metrics show \
  --app 42bank-insights \
  --metric "requests/duration"

# Query logs
az monitor app-insights logs query \
  --app 42bank-insights \
  --query "traces | where message contains 'ERROR' | order by timestamp desc | limit 100"
```

### Model Router Metrics

Monitor in Azure Portal:
- **Requests per minute**: Track throughput
- **Latency (p95, p99)**: Monitor response times
- **Error rate**: Should be < 1%
- **Cost per 1K tokens**: Track spending
- **Model distribution**: Verify routing weights

### Alerts Configuration

```bash
# Create alert for high error rate
az monitor alert create \
  --resource-group 42-bank \
  --name "High-Error-Rate" \
  --condition "greaterThan 0.05" \
  --evaluation-frequency 5m \
  --window-size 15m \
  --action-group "42bank-alerts"

# Create alert for high latency
az monitor alert create \
  --resource-group 42-bank \
  --name "High-Latency" \
  --condition "greaterThan 5000" \
  --evaluation-frequency 5m \
  --window-size 15m \
  --action-group "42bank-alerts"
```

---

## Rollback Plan

### If Model Router Fails

1. **Immediate**: Switch to direct model deployment
   ```bash
   # Update environment variable
   AZURE_AI_MODEL_DEPLOYMENT_NAME=Qwen3.5-35B-A3B
   
   # Restart Container App
   az containerapp revision restart \
     --name 42bank-api \
     --resource-group 42-bank
   ```

2. **Short-term**: Use fallback model
   ```bash
   # Configure in app settings
   FALLBACK_MODEL=Qwen3.5-27B
   ```

3. **Long-term**: Investigate and fix router configuration

### If Database Issues

1. **Point-in-time restore**:
   ```bash
   az cosmosdb restore \
     --account-name 42bank-cosmos \
     --target-database-account-name 42bank-cosmos-restored \
     --restore-timestamp "2024-01-01T00:00:00Z" \
     --resource-group 42-bank
   ```

2. **Switch to restored database**:
   Update `COSMOS_ENDPOINT` in Container App

---

## Post-Deployment Validation

### Functional Tests

```bash
# 1. Health check
curl https://42bank-api.azurecontainerapps.io/health

# 2. User registration
curl -X POST https://42bank-api.azurecontainerapps.io/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test123"}'

# 3. Balance inquiry (via A2A)
curl -X POST https://42bank-api.azurecontainerapps.io/a2a/triage/v1/message \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my balance?"}'
```

### Performance Tests

```bash
# Run load test (100 concurrent users)
hey -z 5m -c 100 https://42bank-api.azurecontainerapps.io/health

# Expected results:
# - Latency p99: < 2s
# - Error rate: < 1%
# - Throughput: > 50 req/s
```

### Security Tests

- [ ] JWT validation working
- [ ] CORS configured correctly
- [ ] Rate limiting enforced
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] TLS 1.3 enforced

---

## Maintenance

### Daily Checks

- [ ] Review error logs in Application Insights
- [ ] Check Model Router metrics (latency, errors)
- [ ] Monitor Cosmos DB RU consumption
- [ ] Verify backup completion

### Weekly Tasks

- [ ] Review cost reports
- [ ] Analyze slow queries
- [ ] Check for security updates
- [ ] Review and rotate secrets if needed

### Monthly Tasks

- [ ] Disaster recovery test
- [ ] Performance benchmarking
- [ ] Dependency updates
- [ ] Security audit

---

## Support & Contacts

### Critical Issues

1. **Production Down**: Contact on-call engineer
2. **Security Incident**: Follow security playbook
3. **Data Loss**: Initiate DR procedure

### Documentation

- [Azure AI Foundry Docs](https://learn.microsoft.com/azure/ai-foundry/)
- [Model Router Guide](https://learn.microsoft.com/azure/ai-foundry/model-router)
- [Cosmos DB Docs](https://learn.microsoft.com/azure/cosmos-db/)
- [Container Apps Docs](https://learn.microsoft.com/azure/container-apps/)

---

**Last Updated**: 2026-03-14  
**Version**: 2.0 (Model Router)
