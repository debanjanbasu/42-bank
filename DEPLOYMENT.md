# Deployment Guide: Azure AI Agents

This guide provides instructions for deploying the 42 Bank Agentic Platform to **Azure AI Foundry** using the **Azure AI Agents Service** (Hosted Agents).

## ☁️ Cloud Architecture

| Feature | Local Mode | Hosted Mode |
| :--- | :--- | :--- |
| **Model Hosting** | Foundry Local (Localhost) | Azure AI Agents Service (Cloud) |
| **Client** | `OpenAIChatClient` | `AzureAIClient` |
| **Identity** | Local `.sk` Wallet | Local `.sk` Wallet (Client-side) |
| **Storage** | SQLite | Azure Cosmos DB (Recommended) |
| **Audit** | Local `audit_service.py` | Azure Functions + Change Feed |

## ⚙️ Configuration

The platform uses environment variables to connect to Azure services. Update your `.env` with the following:

```env
# Azure AI Project Settings
AZURE_AI_PROJECT_ENDPOINT=https://<your-project>.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

- **AZURE_AI_PROJECT_ENDPOINT**: Found in the Azure AI Foundry project settings.
- **AZURE_AI_MODEL_DEPLOYMENT_NAME**: The name of your deployed model (e.g. `gpt-4o`).

## 🔐 Authentication
The platform uses `DefaultAzureCredential`. When running in `hosted` mode, it pro-actively uses your Azure CLI session:
```bash
az login
uv run main.py --user alice --mode hosted
```

## 🏦 Cloud Ledger (Azure Cosmos DB)

For production-scale transaction storage, we recommend migrating the `LedgerEngine` to **Azure Cosmos DB for NoSQL**:
- **Free Tier**: 1,000 RU/s and 25 GB storage (Free Forever).
- **Change Feed**: Native support for pro-active agent triggering (e.g. Fraud Detection).

### Migration Steps
1. Create a Cosmos DB account in the Azure Portal.
2. Implement the `CosmosLedgerEngine` using `azure-cosmos` (stub provided in `ledger.py`).
3. Point the `BankingTools` to the new engine.

## 🛡️ Post-Quantum Readiness
The **ML-DSA-44** signatures implemented in this prototype ensure that your cloud-hosted banking workflows are protected against the threat of future quantum computers. Your private keys never leave the client environment, maintaining a non-custodial security model even when using hosted AI agents.
