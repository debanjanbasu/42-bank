# 42-Bank Deployment Guide

## Prerequisites

- Azure CLI installed
- Docker installed
- Python 3.10+ with uv
- Node.js for mobile app

## Step 1: Build Container

```bash
docker buildx build --platform linux/amd64 -t 42bank:latest .
```

## Step 2: Create ACR and Push

```bash
# Create ACR
az acr create --resource-group 42-bank --name 42bankacr --sku Basic --admin-enabled true

# Login and push
az acr login --name 42bankacr
docker tag 42bank:latest 42bankacr.azurecr.io/42bank:latest
docker push 42bankacr.azurecr.io/42bank:latest
```

## Step 3: Update Container App

```bash
# Update image
az containerapp update \
  --name bank42api \
  --resource-group 42-bank \
  --image 42bankacr.azurecr.io/42bank:latest

# Set environment variables
az containerapp update \
  --name bank42api \
  --resource-group 42-bank \
  --set-env-vars \
    COSMOS_ENDPOINT="https://42bank-cosmos-usk6nbovln4w6.documents.azure.com:443/" \
    COSMOS_DATABASE="banking" \
    APP_ENV="production" \
    AZURE_AI_PROJECT_ENDPOINT="https://42-bank-us-east-2-resource.cognitiveservices.azure.com/" \
    AZURE_AI_MODEL_DEPLOYMENT_NAME="model-router"
```

## Step 4: Bootstrap Database

```bash
# Get Cosmos DB key
COSMOS_KEY=$(az cosmosdb keys list --name 42bank-cosmos-usk6nbovln4w6 --resource-group 42-bank --query "primaryMasterKey" -o tsv)

# Set environment
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=https://42bank-cosmos-usk6nbovln4w6.documents.azure.com:443/;AccountKey=$COSMOS_KEY"
export COSMOS_DATABASE="banking"

# Bootstrap
uv run python bootstrap_hackathon.py
```

## Step 5: Test Deployment

```bash
# Get app URL
APP_URL=$(az containerapp show --name bank42api --resource-group 42-bank --query "properties.configuration.ingress.fqdn" -o tsv)

# Test health
curl -H "x-api-key: hackathon-demo-key-2024" https://$APP_URL/api/health

# Expected: {"status": "healthy", "service": "42-bank-api"}
```

## Step 6: Configure Mobile App

Update `mobile/app.json`:

```json
{
  "extra": {
    "apiUrl": "https://bank42api.calmdesert-cd3f3a1f.eastus.azurecontainerapps.io",
    "a2aUrl": "https://bank42api.calmdesert-cd3f3a1f.eastus.azurecontainerapps.io"
  }
}
```

Then run:
```bash
cd mobile
npm install
npx expo start
```

## Troubleshooting

**Container not starting:**
```bash
az containerapp logs show --name bank42api --resource-group 42-bank
```

**Database connection failed:**
- Verify Cosmos DB endpoint is correct
- Check firewall settings
- Ensure connection string is valid

**Mobile app won't connect:**
- Use same network for phone and computer
- Check URLs in app.json
- Try Expo Go app QR code scan

## Cleanup

After hackathon:
```bash
az group delete --name 42-bank --yes --no-wait
```
