# Production Deployment Checklist

> **Important**: The Model Router is **pre-deployed**. Do not attempt to recreate it during application deployment.

## Pre-Deployment Verification

### 1. Verify Pre-Deployed Resources (DO NOT RECREATE)

```bash
# ✅ Model Router (already deployed)
az ai model-router show \
  --name model-router \
  --resource-group 42-bank \
  --workspace-name 42-bank

# ✅ Model Router Endpoint
curl -X POST "https://42-bank-us-east-2-resource.cognitiveservices.azure.com/openai/deployments/model-router/chat/completions?api-version=2024-05-01-preview" \
  -H "Authorization: Bearer $AZURE_AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Test"}], "max_tokens": 10}'
```

### 2. Deploy Infrastructure (If Not Already Deployed)

```bash
# Deploy Bicep template (one-time only)
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters \
    environment=production \
    jwtSecret=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
```

### 3. Configure Environment Variables

```bash
# Production environment
export AZURE_AI_PROJECT_ENDPOINT=https://42-bank-us-east-2-resource.cognitiveservices.azure.com/
export AZURE_AI_MODEL_DEPLOYMENT_NAME=model-router
export COSMOS_ENDPOINT=https://42bank-cosmos.documents.azure.com:443/
export COSMOS_DATABASE=banking
export APP_ENV=production
```

### 4. Initialize Database

```bash
# Set connection string
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=...;AccountKey=..."

# Run bootstrap
uv run python bootstrap.py
```

### 5. Deploy Application

```bash
# Build and push container
docker build -t 42bank:latest .
docker tag 42bank:latest 42bankregistry.azurecr.io/42bank:latest
docker push 42bankregistry.azurecr.io/42bank:latest

# Update Container App
az containerapp update \
  --name 42bank-api \
  --resource-group 42-bank \
  --image 42bankregistry.azurecr.io/42bank:latest
```

### 6. Verify Deployment

```bash
# Health check
curl https://42bank-api.azurecontainerapps.io/health

# Test Model Router connectivity
curl -X POST "https://42-bank-us-east-2-resource.cognitiveservices.azure.com/openai/deployments/model-router/chat/completions?api-version=2024-05-01-preview" \
  -H "Authorization: Bearer $AZURE_AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Production test"}], "max_tokens": 10}'
```

---

## Rollback Plan

If Model Router issues occur:

```bash
# 1. Temporarily bypass router (use direct model)
export AZURE_AI_MODEL_DEPLOYMENT_NAME=Qwen3.5-35B-A3B

# 2. Restart Container App
az containerapp revision restart \
  --name 42bank-api \
  --resource-group 42-bank

# 3. Contact infrastructure team to investigate Model Router
```

---

## Contact

- **Infrastructure Team**: For Model Router issues
- **DevOps Team**: For deployment issues
- **Security Team**: For security incidents

**Last Updated**: 2026-03-14
