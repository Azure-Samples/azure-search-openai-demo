targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param appServicePlanName string = ''
param backendServiceName string = ''
param resourceGroupName string = ''

param applicationInsightsName string = ''

param storageAccountName string = ''
param storageResourceGroupName string = ''
param storageResourceGroupLocation string = location
param storageContainerName string = 'content'
param storageSkuName string // Set in main.parameters.json

@allowed(['azure', 'openai'])
param openAiHost string // Set in main.parameters.json

param openAiServiceName string = ''
param openAiResourceGroupName string = ''
@description('Location for the OpenAI resource group')
@allowed(['canadaeast', 'eastus', 'eastus2', 'francecentral', 'switzerlandnorth', 'uksouth', 'japaneast', 'northcentralus'])
@metadata({
  azd: {
    type: 'location'
  }
})
param openAiResourceGroupLocation string

param openAiSkuName string = 'S0'

param openAiApiKey string = ''
param openAiApiOrganization string = ''

param formRecognizerServiceName string = ''
param formRecognizerResourceGroupName string = ''
param formRecognizerResourceGroupLocation string = location

param formRecognizerSkuName string = 'S0'

param chatGptDeploymentName string // Set in main.parameters.json
param chatGptDeploymentCapacity int = 30
param chatGptModelName string = (openAiHost == 'azure') ? 'gpt-35-turbo' : 'gpt-3.5-turbo'
param chatGptModelVersion string = '0613'
param embeddingDeploymentName string // Set in main.parameters.json
param embeddingDeploymentCapacity int = 30
param embeddingModelName string = 'text-embedding-ada-002'

// Used for the optional login and document level access control system
param useAuthentication bool = false
param serverAppId string = ''
@secure()
param serverAppSecret string = ''
param clientAppId string = ''

// Used for optional CORS support for alternate frontends
param allowedOrigin string = '' // should start with https://, shouldn't end with a /

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Use Application Insights for monitoring and performance tracing')
param useApplicationInsights bool = false

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

resource formRecognizerResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(formRecognizerResourceGroupName)) {
  name: !empty(formRecognizerResourceGroupName) ? formRecognizerResourceGroupName : resourceGroup.name
}

resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : resourceGroup.name
}

// Monitor application with Azure Monitor
module monitoring './core/monitor/monitoring.bicep' = if (useApplicationInsights) {
  name: 'monitoring'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
  }
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan 'core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: resourceGroup
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'B1'
      capacity: 1
    }
    kind: 'linux'
  }
}

// The application frontend
module backend 'core/host/appservice.bicep' = {
  name: 'web'
  scope: resourceGroup
  params: {
    name: !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    appCommandLine: 'python3 -m gunicorn main:app'
    scmDoBuildDuringDeployment: true
    managedIdentity: true
    allowedOrigins: [allowedOrigin]
    appSettings: {
      AZURE_STORAGE_ACCOUNT: storage.outputs.name
      AZURE_STORAGE_CONTAINER: storageContainerName
      APPLICATIONINSIGHTS_CONNECTION_STRING: useApplicationInsights ? monitoring.outputs.applicationInsightsConnectionString : ''
      // Shared by all OpenAI deployments
      OPENAI_HOST: openAiHost
      AZURE_OPENAI_EMB_MODEL_NAME: embeddingModelName
      AZURE_OPENAI_CHATGPT_MODEL: chatGptModelName
      // Specific to Azure OpenAI
      AZURE_OPENAI_SERVICE: openAiHost == 'azure' ? openAi.outputs.name : ''
      AZURE_OPENAI_CHATGPT_DEPLOYMENT: chatGptDeploymentName
      AZURE_OPENAI_EMB_DEPLOYMENT: embeddingDeploymentName
      // Used only with non-Azure OpenAI deployments
      OPENAI_API_KEY: openAiApiKey
      OPENAI_ORGANIZATION: openAiApiOrganization
      // Optional login and document level access control system
      AZURE_USE_AUTHENTICATION: useAuthentication
      AZURE_SERVER_APP_ID: serverAppId
      AZURE_SERVER_APP_SECRET: serverAppSecret
      AZURE_CLIENT_APP_ID: clientAppId
      AZURE_TENANT_ID: tenant().tenantId
      // CORS support, for frontends on other hosts
      ALLOWED_ORIGIN: allowedOrigin
    }
  }
}

module openAi 'core/ai/cognitiveservices.bicep' = if (openAiHost == 'azure') {
  name: 'openai'
  scope: openAiResourceGroup
  params: {
    name: !empty(openAiServiceName) ? openAiServiceName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    location: openAiResourceGroupLocation
    tags: tags
    sku: {
      name: openAiSkuName
    }
    deployments: [
      {
        name: chatGptDeploymentName
        model: {
          format: 'OpenAI'
          name: chatGptModelName
          version: chatGptModelVersion
        }
        sku: {
          name: 'Standard'
          capacity: chatGptDeploymentCapacity
        }
      }
      {
        name: embeddingDeploymentName
        model: {
          format: 'OpenAI'
          name: embeddingModelName
          version: '2'
        }
        capacity: embeddingDeploymentCapacity
      }
    ]
  }
}

module formRecognizer 'core/ai/cognitiveservices.bicep' = {
  name: 'formrecognizer'
  scope: formRecognizerResourceGroup
  params: {
    name: !empty(formRecognizerServiceName) ? formRecognizerServiceName : '${abbrs.cognitiveServicesFormRecognizer}${resourceToken}'
    kind: 'FormRecognizer'
    location: formRecognizerResourceGroupLocation
    tags: tags
    sku: {
      name: formRecognizerSkuName
    }
  }
}

module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: storageResourceGroup
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: storageResourceGroupLocation
    tags: tags
    publicNetworkAccess: 'Enabled'
    sku: {
      name: storageSkuName
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 2
    }
    containers: [
      {
        name: storageContainerName
        publicAccess: 'None'
      }
    ]
  }
}

// USER ROLES
module openAiRoleUser 'core/security/role.bicep' = if (openAiHost == 'azure') {
  scope: openAiResourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'User'
  }
}

module formRecognizerRoleUser 'core/security/role.bicep' = {
  scope: formRecognizerResourceGroup
  name: 'formrecognizer-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'User'
  }
}

module storageRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'User'
  }
}

module storageContribRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-contribrole-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    principalType: 'User'
  }
}


// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = if (openAiHost == 'azure') {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleBackend 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

// Shared by all OpenAI deployments
output OPENAI_HOST string = openAiHost
output AZURE_OPENAI_EMB_MODEL_NAME string = embeddingModelName
output AZURE_OPENAI_CHATGPT_MODEL string = chatGptModelName
// Specific to Azure OpenAI
output AZURE_OPENAI_SERVICE string = (openAiHost == 'azure') ? openAi.outputs.name : ''
output AZURE_OPENAI_RESOURCE_GROUP string = (openAiHost == 'azure') ? openAiResourceGroup.name : ''
output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = (openAiHost == 'azure') ? chatGptDeploymentName : ''
output AZURE_OPENAI_EMB_DEPLOYMENT string = (openAiHost == 'azure') ? embeddingDeploymentName : ''
// Used only with non-Azure OpenAI deployments
output OPENAI_API_KEY string = (openAiHost == 'openai') ? openAiApiKey : ''
output OPENAI_ORGANIZATION string = (openAiHost == 'openai') ? openAiApiOrganization : ''

output AZURE_FORMRECOGNIZER_SERVICE string = formRecognizer.outputs.name
output AZURE_FORMRECOGNIZER_RESOURCE_GROUP string = formRecognizerResourceGroup.name

output AZURE_STORAGE_ACCOUNT string = storage.outputs.name
output AZURE_STORAGE_CONTAINER string = storageContainerName
output AZURE_STORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output BACKEND_URI string = backend.outputs.uri
