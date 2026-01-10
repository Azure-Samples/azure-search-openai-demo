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

// Authorization parameters
@description('The Entra ID application (client) ID for App Service Authentication')
param authClientId string

@description('The Entra ID identifier URI for App Service Authentication')
param authIdentifierUri string

@description('The Azure AD tenant ID for App Service Authentication')
param authTenantId string

@description('The application client ID of the Search service user-assigned managed identity')
param searchUserAssignedIdentityClientId string

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
  AZURE_CLIENT_ID: identityClientId
}

// Optional Application Insights settings
var appInsightsSettings = !empty(applicationInsightsName) ? {
  APPLICATIONINSIGHTS_AUTHENTICATION_STRING: applicationInsightsIdentity
  APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.?properties.ConnectionString ?? ''
} : {}

var easyAuthSettings = {
    OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID: identityClientId
    WEBSITE_AUTH_PRM_DEFAULT_WITH_SCOPES: '${authIdentifierUri}/user_impersonation'
    WEBSITE_AUTH_AAD_ALLOWED_TENANTS: authTenantId
}

// Merge all app settings
var allAppSettings = union(appSettings, baseAppSettings, appInsightsSettings, easyAuthSettings)

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
      userAssignedResourceIds: [
        '${identityId}'
      ]
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
resource auth 'Microsoft.Web/sites/config@2022-03-01' = {
  name: '${name}/authsettingsV2'
  dependsOn: [
    functionApp  // Ensure the Function App module completes before configuring authentication
  ]
  properties: {
    globalValidation: {
      requireAuthentication: true
      unauthenticatedClientAction: 'Return401'
      redirectToProvider: 'azureactivedirectory'
    }
    httpSettings: {
      requireHttps: true
      routes: {
        apiPrefix: '/.auth'
      }
      forwardProxy: {
        convention: 'NoProxy'
      }
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          openIdIssuer: '${environment().authentication.loginEndpoint}${authTenantId}/v2.0'
          clientId: authClientId
          clientSecretSettingName: 'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID'
        }
        validation: {
          jwtClaimChecks: {}
          allowedAudiences: [
            authIdentifierUri
          ]
          defaultAuthorizationPolicy: {
            allowedPrincipals: {}
            allowedApplications: [searchUserAssignedIdentityClientId]
          }
        }
        isAutoProvisioned: false
      }
    }
    login: {
      routes: {
        logoutEndpoint: '/.auth/logout'
      }
      tokenStore: {
        enabled: true
        tokenRefreshExtensionHours: 72
        fileSystem: {}
        azureBlobStorage: {}
      }
      preserveUrlFragmentsForLogins: false
      allowedExternalRedirectUrls: []
      cookieExpiration: {
        convention: 'FixedTime'
        timeToExpiration: '08:00:00'
      }
      nonce: {
        validateNonce: true
        nonceExpirationInterval: '00:05:00'
      }
    }
    platform: {
      enabled: true
      runtimeVersion: '~1'
    }
  }
}

// Outputs
output name string = functionApp.outputs.name
output defaultHostname string = functionApp.outputs.defaultHostname
// Expose resourceId for downstream skill auth configuration
output resourceId string = functionApp.outputs.resourceId
output authEnabled bool = !empty(authClientId) && !empty(authIdentifierUri)
