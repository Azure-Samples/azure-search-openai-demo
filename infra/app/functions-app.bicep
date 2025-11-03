// Single function app module
param name string
param location string = resourceGroup().location
param tags object = {}
@description('Name of an existing Application Insights component. Leave empty to disable.')
param applicationInsightsName string
param appServicePlanId string
param appSettings object = {}
param runtimeName string
param runtimeVersion string
param storageAccountName string
param deploymentStorageContainerName string
param instanceMemoryMB int = 2048
param maximumInstanceCount int = 10
param identityId string
param identityClientId string
// App Registration client ID (applicationId) used to secure Function App endpoints (Easy Auth)
param skillAppClientId string = ''
// Audience / identifier URI to validate tokens (e.g. api://<subscriptionId>/<env>-skill)
param skillAppAudience string = ''

// AVM expects authentication.type values: SystemAssignedIdentity | UserAssignedIdentity | StorageAccountConnectionString
// Use UserAssignedIdentity for per-function user-assigned managed identity deployment storage access.
var identityType = 'UserAssignedIdentity'
var kind = 'functionapp,linux'
var applicationInsightsIdentity = 'ClientId=${identityClientId};Authorization=AAD'

// Reference existing resources
resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (!empty(applicationInsightsName)) {
  name: applicationInsightsName
}

// Create base application settings (independent of Application Insights)
var baseAppSettings = {
  // Storage credentials for AzureWebJobsStorage
  AzureWebJobsStorage__credential: 'managedidentity'
  AzureWebJobsStorage__clientId: identityClientId
  AzureWebJobsStorage__blobServiceUri: stg.properties.primaryEndpoints.blob
  AzureWebJobsStorage__queueServiceUri: stg.properties.primaryEndpoints.queue
  AzureWebJobsStorage__tableServiceUri: stg.properties.primaryEndpoints.table
  FUNCTIONS_EXTENSION_VERSION: '~4'
}

// Optional Application Insights settings
var appInsightsSettings = !empty(applicationInsightsName) ? {
  APPLICATIONINSIGHTS_AUTHENTICATION_STRING: applicationInsightsIdentity
  APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.?properties.ConnectionString ?? ''
} : {}

// Surface skill application identifiers for downstream logging/diagnostics (not used for manual validation now that Easy Auth is enabled)
var skillAudienceSettings = (!empty(skillAppClientId) && !empty(skillAppAudience)) ? {
  SKILL_APP_ID: skillAppClientId
  SKILL_APP_AUDIENCE: skillAppAudience
} : {}

// Merge all app settings
var allAppSettings = union(appSettings, baseAppSettings, appInsightsSettings, skillAudienceSettings)

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
      httpsOnly: true
      ftpsState: 'Disabled'
      cors: {
        allowedOrigins: ['https://portal.azure.com']
      }
    }
    appSettingsKeyValuePairs: allAppSettings
  }
}

// Enable Easy Auth (App Service authentication) for Azure Search custom skill access when a skillAppId is provided.
// Based on Microsoft guidance: require authentication, return 401 on unauthenticated, allowed audience api://{applicationId}.
resource auth 'Microsoft.Web/sites/config@2022-03-01' = if (!empty(skillAppClientId) && !empty(skillAppAudience)) {
  name: '${name}/authsettingsV2'
  properties: {
    globalValidation: {
      requireAuthentication: true
      unauthenticatedClientAction: 'Return401'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: skillAppClientId
        }
        validation: {
          allowedAudiences: [ skillAppAudience ]
        }
      }
    }
  }
  dependsOn: [ functionApp ]
}

// Outputs
output name string = functionApp.outputs.name
output defaultHostname string = functionApp.outputs.defaultHostname
// Expose resourceId for downstream skill auth configuration
output resourceId string = functionApp.outputs.resourceId
output authEnabled bool = !empty(skillAppClientId) && !empty(skillAppAudience)
