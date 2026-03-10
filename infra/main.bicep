// Azure deployment for 42-Bank multi-agent banking system
// 
// This template creates:
//   - Azure Cosmos DB account (Serverless)
//   - Database and containers for banking data
//   - Storage account for Container Apps
//   - Container Apps environment + app (system-assigned managed identity)
//   - Log Analytics + Application Insights
//
// No Key Vault — JWT_SECRET stored as Container Apps encrypted secret (free).
// Cosmos DB access via managed identity data-plane RBAC (no keys).
//
// Usage:
//   az deployment sub create --location eastus --template-file main.bicep \
//     --parameters jwtSecret=$(python -c "import secrets; print(secrets.token_urlsafe(48))")

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'eastus'

@description('Environment (dev, staging, production)')
param environment string = 'production'

@description('Cosmos DB account name')
param cosmosAccountName string = '42bank-cosmos'

@description('JWT secret for token signing (stored as Container Apps encrypted secret)')
@secure()
param jwtSecret string

@description('Storage account name (must be globally unique)')
param storageAccountName string = '42bankstorage${uniqueString(subscription().id, location)}'

@description('Container Apps environment name')
param containerAppsEnvName string = '42bank-env'

@description('Container App name')
param containerAppName string = '42bank-api'

@description('Container image to deploy (e.g. myregistry.azurecr.io/42bank:latest)')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// Variables
var resourceGroupName = '42-bank'
var databaseName = 'banking'
var uniqueSuffix = uniqueString(subscription().id, location)

// ============ Resource Group ============
// Assumes resource group already exists (created manually or via portal)
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' existing = {
  name: resourceGroupName
}

// ============ Cosmos DB (Serverless) ============
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: '${cosmosAccountName}-${uniqueSuffix}'
  location: location
  resourceGroup: rg.name
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    isVirtualNetworkFilterEnabled: true
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
      maxIntervalInSeconds: 5
      maxStalenessPrefix: 100
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    backupPolicy: {
      type: 'Continuous'
    }
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// Database
resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Users container
resource usersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: {
        paths: ['/token']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/username/*'
          }
          {
            path: '/accounts/*'
          }
        ]
        excludedPaths: [
          {
            path: '/\"_etag\"/?'
          }
        ]
      }
    }
  }
}

// Transactions container
resource transactionsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'transactions'
  properties: {
    resource: {
      id: 'transactions'
      partitionKey: {
        paths: ['/timestamp']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/sender/*'
          }
          {
            path: '/recipient/*'
          }
          {
            path: '/timestamp/*'
          }
        ]
      }
      defaultTtl: -1 // No expiration
    }
  }
}

// Pending requests container
resource pendingRequestsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'pending_requests'
  properties: {
    resource: {
      id: 'pending_requests'
      partitionKey: {
        paths: ['/request_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/recipient/*'
          }
          {
            path: '/status/*'
          }
        ]
      }
    }
  }
}

// Products container
resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'products'
  properties: {
    resource: {
      id: 'products'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
    }
  }
}

// ============ Storage Account ============
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  resourceGroup: rg.name
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// ============ Container Apps Environment ============
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppsEnvName
  location: location
  resourceGroup: rg.name
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.workspaceId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// ============ Log Analytics ============
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '42bank-logs-${uniqueSuffix}'
  location: location
  resourceGroup: rg.name
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    // Ingestion must remain Enabled so agents and Container Apps can write logs
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// ============ Application Insights ============
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '42bank-insights-${uniqueSuffix}'
  location: location
  resourceGroup: rg.name
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    // Ingestion must remain Enabled so Application Insights SDK can send telemetry
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// ============ Container App ============
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  resourceGroup: rg.name
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      secrets: [
        {
          // Stored encrypted in Container Apps platform — no Key Vault needed
          name: 'jwt-secret'
          value: jwtSecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: '42bank-api'
          image: containerImage
          env: [
            { name: 'COSMOS_ENDPOINT'; value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DATABASE'; value: databaseName }
            { name: 'APP_ENV'; value: environment }
            { name: 'JWT_SECRET'; secretRef: 'jwt-secret' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'; value: insights.properties.ConnectionString }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
    }
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// ============ RBAC: Managed Identity → Cosmos DB ============
// "Cosmos DB Built-in Data Contributor" (data-plane role, no key needed)
resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  parent: cosmos
  name: guid(cosmos.id, containerApp.identity.principalId, 'cosmos-data-contributor')
  properties: {
    roleDefinitionId: '/${subscription().subscriptionId}/resourceGroups/${resourceGroupName}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmos.name}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: containerApp.identity.principalId
    scope: cosmos.id
  }
}

output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosAccountId string = cosmos.id
output storageAccountName string = storage.name
output containerAppsEnvironmentId string = containerAppsEnv.id
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output managedIdentityPrincipalId string = containerApp.identity.principalId
output logAnalyticsWorkspaceId string = logAnalytics.properties.workspaceId
output applicationInsightsConnectionString string = insights.properties.ConnectionString
