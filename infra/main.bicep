// Azure deployment for 42-Bank multi-agent banking system
// 
// This template creates:
//   - Azure Cosmos DB account (Serverless)
//   - Database and containers for banking data
//   - Azure Key Vault for secrets
//   - Storage account for Function App
//   - Container Apps environment (if not exists)
//
// Usage:
//   az deployment sub create --location eastus --template-file main.bicep
//
// Prerequisites:
//   - Resource group '42-bank' already exists
//   - AI Foundry project '42-bank' already exists

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'eastus'

@description('Environment (dev, staging, production)')
param environment string = 'production'

@description('Cosmos DB account name')
param cosmosAccountName string = '42bank-cosmos'

@description('Key Vault name')
param keyVaultName string = '42bank-kv'

@description('Storage account name (must be globally unique)')
param storageAccountName string = '42bankstorage${uniqueString(subscription().id, location)}'

@description('Container Apps environment name')
param containerAppsEnvName string = '42bank-env'

@description('Enable public network access for Key Vault (disable in production)')
param keyVaultPublicNetworkAccess string = 'Enabled'

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

// ============ Key Vault ============
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${keyVaultName}-${uniqueSuffix}'
  location: location
  resourceGroup: rg.name
  properties: {
    tenantId: subscription().tenantId
    sku: {
      name: 'standard'
      family: 'A'
    }
    enableSoftDelete: true
    enablePurgeProtection: true
    enableRbacAuthorization: true
    // Set keyVaultPublicNetworkAccess param to 'Disabled' in production for hardened security
    publicNetworkAccess: keyVaultPublicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: []
    }
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// Cosmos connection string secret
resource cosmosConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cosmos-connection-string'
  properties: {
    value: 'AccountEndpoint=${cosmos.properties.documentEndpoint};AccountKey=${cosmos.listKeys().primaryMasterKey}'
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

// ============ Outputs ============
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosConnectionString string = 'AccountEndpoint=${cosmos.properties.documentEndpoint};AccountKey=${cosmos.listKeys().primaryMasterKey}'
output cosmosAccountId string = cosmos.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output storageAccountName string = storage.name
output containerAppsEnvironmentId string = containerAppsEnv.id
output logAnalyticsWorkspaceId string = logAnalytics.properties.workspaceId
output applicationInsightsInstrumentationKey string = insights.properties.InstrumentationKey
