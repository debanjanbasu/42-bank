# Deployment Guide: Azure AI Agents (Hosted Agents)

This guide provides instructions for deploying the 42 Bank Agentic Platform to **Azure AI Foundry** using the **Azure AI Agents Service** (Hosted Agents).

## Prerequisites

1.  **Azure Subscription**: You need an active Azure subscription.
2.  **Azure AI Foundry Project**: Create a project in [Azure AI Foundry](https://ai.azure.com).
3.  **Model Deployment**: Deploy a model (e.g., `gpt-4o`) within your project.
4.  **Azure CLI**: Install the Azure CLI and sign in using `az login`.

## Configuration

The platform uses environment variables to connect to the Azure AI Agents Service. Update your `.env` file or set them in your environment:

```env
# Azure AI Project Settings
AZURE_AI_PROJECT_ENDPOINT=https://<your-project-name>.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

-   `AZURE_AI_PROJECT_ENDPOINT`: The Discovery URL or Project Endpoint found in the Azure AI Foundry project settings.
-   `AZURE_AI_MODEL_DEPLOYMENT_NAME`: The name of the model deployment you want to use.

## Authentication

The platform uses `DefaultAzureCredential` from the `azure-identity` library. When running locally in `hosted` mode, it will use your Azure CLI credentials.

Ensure you have the necessary permissions (e.g., `Azure AI Developer` or `Contributor`) on the project resource.

## Running in Hosted Mode

To start the platform using the hosted Azure AI Agents Service:

```bash
uv run main.py --user alice --mode hosted
```

## Architecture Differences

| Feature | Local Mode | Hosted Mode |
| :--- | :--- | :--- |
| **Model Hosting** | Foundry Local (Localhost) | Azure AI Agents Service (Azure) |
| **Client** | `OpenAIResponsesClient` | `AzureAIClient` |
| **Tools** | Local Python functions | Local Python functions (executed via Agent Framework) |
| **Handoffs** | Local Orchestration | Local Orchestration (via `HandoffBuilder`) |

## Cloud Storage (Ledger)

For storing transactions in production, we recommend **Azure Cosmos DB for NoSQL**:
- **Free Tier**: 1,000 RU/s and 25 GB storage (Free Forever).
- **Performance**: Single-digit millisecond latency for globally distributed data.
- **Scalability**: Seamlessly handles peaks in transaction volume.

### Migrating to Cosmos DB
1.  Create a Cosmos DB account in the Azure Portal.
2.  Add `AZURE_COSMOS_ENDPOINT` and `AZURE_COSMOS_KEY` to your `.env`.
3.  Implement the `CosmosLedgerEngine` class in `ledger.py` (stubs are already provided).
