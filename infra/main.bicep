// Azure deployment for 42-Bank multi-agent banking system
// Simplified for hackathon deployment

targetScope = 'resourceGroup'

@description('Azure region for all resources')
param location string = 'eastus'

@description('Environment (dev, staging, production)')
param environment string = 'production'

@description('Cosmos DB account name')
param cosmosAccountName string = '42bank-cosmos'

@description('JWT secret for token signing')
@secure()
param jwtSecret string

@description('Storage account name')
param storageAccountName string = '42bank${uniqueString(resourceGroup().id)}'

@description('Container Apps environment name')
param containerAppsEnvName string = '42bank-env'

@description('Container App name')
param containerAppName string = 'bank42api'

@description('Container image to deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Container Registry name')
param acrName string = '42bankacr${uniqueString(resourceGroup().id)}'

var databaseName = 'banking'
var uniqueSuffix = uniqueString(resourceGroup().id)

// Cosmos DB (Serverless)
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: '${cosmosAccountName}-${uniqueSuffix}'
  location: location
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

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource usersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: {
        paths: ['/username']
        kind: 'Hash'
      }
    }
  }
}

resource changeFeedContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'change_feed'
  properties: {
    resource: {
      id: 'change_feed'
      partitionKey: {
        paths: ['/event_type']
        kind: 'Hash'
      }
    }
  }
}

resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'products'
  properties: {
    resource: {
      id: 'products'
      partitionKey: {
        paths: ['/type']
        kind: 'Hash'
      }
    }
  }
}

// Storage Account
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
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

// Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// Log Analytics
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '42bank-logs-${uniqueSuffix}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// Application Insights
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '42bank-insights-${uniqueSuffix}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// Container Apps Environment
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
  tags: {
    Environment: environment
    Project: '42-bank'
  }
}

// Get ACR credentials
var acrCredentials = az acr credential show --name acrName --resource-group resourceGroup().name

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
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
          name: 'jwt-secret'
          value: jwtSecret
        }
      ]
      registries: [
        {
          server: acr.properties.loginServer
          username: 'admin'
          passwordSecretRef: 'acr-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: '42bank-api'
          image: containerImage
          env: [
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmos.properties.documentEndpoint
            }
            {
              name: 'COSMOS_DATABASE'
              value: databaseName
            }
            {
              name: 'APP_ENV'
              value: environment
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'jwt-secret'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: insights.properties.ConnectionString
            }
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

// Outputs
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosAccountId string = cosmos.id
output storageAccountName string = storage.name
output containerAppsEnvironmentId string = containerAppsEnv.id
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output managedIdentityPrincipalId string = containerApp.identity.principalId
output logAnalyticsWorkspaceId string = logAnalytics.properties.customerId
output applicationInsightsConnectionString string = insights.properties.ConnectionString
