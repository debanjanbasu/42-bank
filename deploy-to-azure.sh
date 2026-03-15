#!/bin/bash
# 42-Bank Hackathon Deployment Script
# Deploys the app to Azure Container Apps

set -e

echo "🚀 42-Bank Hackathon Deployment"
echo "================================"
echo ""

# Configuration
RESOURCE_GROUP="42-bank"
CONTAINER_APP_NAME="bank42api"
LOCATION="eastus"
ACR_NAME="42bankacr$(openssl rand -hex 4)"

# Step 1: Check if resource group exists
echo "1️⃣  Checking resource group..."
if ! az group exists --name $RESOURCE_GROUP; then
    echo "   Creating resource group..."
    az group create --name $RESOURCE_GROUP --location $LOCATION
else
    echo "   ✅ Resource group exists"
fi

# Step 2: Deploy infrastructure
echo ""
echo "2️⃣  Deploying infrastructure..."
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file infra/main.bicep \
    --parameters jwtSecret=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

echo "   ✅ Infrastructure deployed"

# Step 3: Create Container Registry
echo ""
echo "3️⃣  Creating Container Registry..."
if ! az acr show --name ${ACR_NAME} --resource-group $RESOURCE_GROUP 2>/dev/null; then
    az acr create \
        --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME \
        --sku Basic \
        --admin-enabled true
    echo "   ✅ Container Registry created: $ACR_NAME"
else
    echo "   ✅ Container Registry exists"
fi

# Get ACR name
ACR_NAME=$(az acr list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "   Using ACR: $ACR_NAME"

# Step 4: Build and push container
echo ""
echo "4️⃣  Building and pushing container..."
az acr build \
    --registry $ACR_NAME \
    --image 42bank:latest \
    --file Dockerfile .

echo "   ✅ Container built and pushed"

# Step 5: Update Container App
echo ""
echo "5️⃣  Updating Container App..."
acr_login_server=$(az acr show --name $ACR_NAME --query "loginServer" -o tsv)
az containerapp update \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --image ${acr_login_server}/42bank:latest

echo "   ✅ Container App updated"

# Step 6: Get app URL
echo ""
echo "6️⃣  Getting deployment info..."
APP_URL=$(az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv)

COSMOS_ENDPOINT=$(az cosmosdb show \
    --name 42bank-cosmos-* \
    --resource-group $RESOURCE_GROUP \
    --query "documentEndpoint" \
    -o tsv)

echo ""
echo "================================"
echo "✅ Deployment Complete!"
echo "================================"
echo ""
echo "App URL: https://$APP_URL"
echo "Cosmos DB: $COSMOS_ENDPOINT"
echo ""
echo "Next steps:"
echo "1. Set environment variables:"
echo "   export COSMOS_ENDPOINT=$COSMOS_ENDPOINT"
echo "   export COSMOS_DATABASE=banking"
echo "   export AZURE_COSMOS_CONNECTION_STRING=\"AccountEndpoint=\$COSMOS_ENDPOINT;AccountKey=<your-key>\""
echo ""
echo "2. Bootstrap database:"
echo "   uv run python bootstrap_hackathon.py"
echo ""
echo "3. Test deployment:"
echo "   curl -H \"x-api-key: hackathon-demo-key-2024\" https://$APP_URL/api/health"
echo ""
echo "4. See DEMO.md for full demo instructions"
echo ""
