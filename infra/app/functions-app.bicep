// Single function app module
param name string
param location string = resourceGroup().location
param tags object = {}
param applicationInsightsName string
param appServicePlanId string
param appSettings object = {}
param runtimeName string
param runtimeVersion string
param storageAccountName string
param deploymentStorageContainerName string
param instanceMemoryMB int = 2048
param maximumInstanceCount int = 100
param identityId string
param identityClientId string
param functionTimeout string = '00:05:00'

var identityType = 'UserAssigned'
var kind = 'functionapp,linux'
var applicationInsightsIdentity = 'ClientId=${identityClientId};Authorization=AAD'

// Reference existing resources
resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

// Create base application settings
var baseAppSettings = {
  // Storage credentials for AzureWebJobsStorage
  AzureWebJobsStorage__credential: 'managedidentity'
  AzureWebJobsStorage__clientId: identityClientId
  AzureWebJobsStorage__blobServiceUri: stg.properties.primaryEndpoints.blob
  AzureWebJobsStorage__queueServiceUri: stg.properties.primaryEndpoints.queue
  AzureWebJobsStorage__tableServiceUri: stg.properties.primaryEndpoints.table

  // Application Insights
  APPLICATIONINSIGHTS_AUTHENTICATION_STRING: applicationInsightsIdentity
  APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString

  // Function timeout
  FUNCTIONS_EXTENSION_VERSION: '~4'
  FUNCTIONS_WORKER_RUNTIME: runtimeName
}

// Merge all app settings
var allAppSettings = union(appSettings, baseAppSettings)

// Create Flex Consumption Function App using AVM
module functionApp 'br/public:avm/res/web/site:0.15.1' = {
  name: '${name}-func-app'
  params: {
    kind: kind
    name: name
    location: location
    tags: tags
    serverFarmResourceId: appServicePlanId
    managedIdentities: {
      userAssignedResourceIds: [identityId]
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${stg.properties.primaryEndpoints.blob}${deploymentStorageContainerName}'
          authentication: {
            type: identityType
            userAssignedIdentityResourceId: identityId
          }
        }
      }
      scaleAndConcurrency: {
        instanceMemoryMB: instanceMemoryMB
        maximumInstanceCount: maximumInstanceCount
      }
      runtime: {
        name: runtimeName
        version: runtimeVersion
      }
    }
    siteConfig: {
      alwaysOn: false
      functionAppScaleLimit: maximumInstanceCount
      cors: {
        allowedOrigins: ['https://portal.azure.com']
      }
    }
    appSettingsKeyValuePairs: allAppSettings
  }
}

// Outputs
output name string = functionApp.outputs.name
output defaultHostname string = functionApp.outputs.defaultHostname
