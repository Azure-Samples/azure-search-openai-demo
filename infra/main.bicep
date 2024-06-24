targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param appServicePlanName string = '' // Set in main.parameters.json
param backendServiceName string = '' // Set in main.parameters.json
param resourceGroupName string = '' // Set in main.parameters.json

param applicationInsightsDashboardName string = '' // Set in main.parameters.json
param applicationInsightsName string = '' // Set in main.parameters.json
param logAnalyticsName string = '' // Set in main.parameters.json

param searchServiceName string = '' // Set in main.parameters.json
param searchServiceResourceGroupName string = '' // Set in main.parameters.json
param searchServiceLocation string = '' // Set in main.parameters.json
// The free tier does not support managed identity (required) or semantic search (optional)
@allowed([ 'free', 'basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2' ])
param searchServiceSkuName string // Set in main.parameters.json
param searchIndexName string // Set in main.parameters.json
param searchQueryLanguage string // Set in main.parameters.json
param searchQuerySpeller string // Set in main.parameters.json
param searchServiceSemanticRankerLevel string // Set in main.parameters.json
var actualSearchServiceSemanticRankerLevel = (searchServiceSkuName == 'free') ? 'disabled' : searchServiceSemanticRankerLevel

param storageAccountName string = '' // Set in main.parameters.json
param storageResourceGroupName string = '' // Set in main.parameters.json
param storageResourceGroupLocation string = location
param storageContainerName string = 'content'
param storageSkuName string // Set in main.parameters.json

param userStorageAccountName string = ''
param userStorageContainerName string = 'user-content'

param appServiceSkuName string // Set in main.parameters.json

@allowed([ 'azure', 'openai', 'azure_custom' ])
param openAiHost string // Set in main.parameters.json
param isAzureOpenAiHost bool = startsWith(openAiHost, 'azure')
param deployAzureOpenAi bool = openAiHost == 'azure'
param azureOpenAiCustomUrl string = ''
param azureOpenAiApiVersion string = ''
@secure()
param azureOpenAiApiKey string = ''
param openAiServiceName string = ''
param openAiResourceGroupName string = ''

param speechServiceResourceGroupName string = ''
param speechServiceLocation string = ''
param speechServiceName string = ''
param speechServiceSkuName string // Set in main.parameters.json
param useGPT4V bool = false

@description('Location for the OpenAI resource group')
@allowed([ 'canadaeast', 'eastus', 'eastus2', 'francecentral', 'switzerlandnorth', 'uksouth', 'japaneast', 'northcentralus', 'australiaeast', 'swedencentral' ])
@metadata({
  azd: {
    type: 'location'
  }
})
param openAiResourceGroupLocation string

param openAiSkuName string = 'S0'

@secure()
param openAiApiKey string = ''
param openAiApiOrganization string = ''

param documentIntelligenceServiceName string = '' // Set in main.parameters.json
param documentIntelligenceResourceGroupName string = '' // Set in main.parameters.json

// Limited regions for new version:
// https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-layout
@description('Location for the Document Intelligence resource group')
@allowed([ 'eastus', 'westus2', 'westeurope' ])
@metadata({
  azd: {
    type: 'location'
  }
})
param documentIntelligenceResourceGroupLocation string

param documentIntelligenceSkuName string // Set in main.parameters.json

param computerVisionServiceName string = '' // Set in main.parameters.json
param computerVisionResourceGroupName string = '' // Set in main.parameters.json
param computerVisionResourceGroupLocation string = '' // Set in main.parameters.json
param computerVisionSkuName string // Set in main.parameters.json

param chatGptModelName string = ''
param chatGptDeploymentName string = ''
param chatGptDeploymentVersion string = ''
param chatGptDeploymentCapacity int = 0
var chatGpt = {
  modelName: !empty(chatGptModelName) ? chatGptModelName : startsWith(openAiHost, 'azure') ? 'gpt-35-turbo' : 'gpt-3.5-turbo'
  deploymentName: !empty(chatGptDeploymentName) ? chatGptDeploymentName : 'chat'
  deploymentVersion: !empty(chatGptDeploymentVersion) ? chatGptDeploymentVersion : '0613'
  deploymentCapacity: chatGptDeploymentCapacity != 0 ? chatGptDeploymentCapacity : 30
}

param embeddingModelName string = ''
param embeddingDeploymentName string = ''
param embeddingDeploymentVersion string = ''
param embeddingDeploymentCapacity int = 0
param embeddingDimensions int = 0
var embedding = {
  modelName: !empty(embeddingModelName) ? embeddingModelName : 'text-embedding-ada-002'
  deploymentName: !empty(embeddingDeploymentName) ? embeddingDeploymentName : 'embedding'
  deploymentVersion: !empty(embeddingDeploymentVersion) ? embeddingDeploymentVersion : '2'
  deploymentCapacity: embeddingDeploymentCapacity != 0 ? embeddingDeploymentCapacity : 30
  dimensions: embeddingDimensions != 0 ? embeddingDimensions : 1536
}

param gpt4vModelName string = 'gpt-4o'
param gpt4vDeploymentName string = 'gpt-4o'
param gpt4vModelVersion string = '2024-05-13'
param gpt4vDeploymentCapacity int = 10

param tenantId string = tenant().tenantId
param authTenantId string = ''

// Used for the optional login and document level access control system
param useAuthentication bool = false
param enforceAccessControl bool = false
param enableGlobalDocuments bool = false
param enableUnauthenticatedAccess bool = false
param serverAppId string = ''
@secure()
param serverAppSecret string = ''
param clientAppId string = ''
@secure()
param clientAppSecret string = ''

// Used for optional CORS support for alternate frontends
param allowedOrigin string = '' // should start with https://, shouldn't end with a /

@allowed([ 'None', 'AzureServices' ])
@description('If allowedIp is set, whether azure services are allowed to bypass the storage and AI services firewall.')
param bypass string = 'AzureServices'

@description('Public network access value for all deployed resources')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Enabled'

@description('Add a private endpoints for network connectivity')
param usePrivateEndpoint bool = false

@description('Provision a VM to use for private endpoint connectivity')
param provisionVm bool = false
param vmUserName string = ''
@secure()
param vmPassword string = ''
param vmOsVersion string = ''
param vmOsPublisher string = ''
param vmOsOffer string = ''
@description('Size of the virtual machine.')
param vmSize string = 'Standard_DS1_v2'

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Use Application Insights for monitoring and performance tracing')
param useApplicationInsights bool = false

@description('Use speech recognition feature in browser')
param useSpeechInputBrowser bool = false
@description('Use speech synthesis in browser')
param useSpeechOutputBrowser bool = false
@description('Use Azure speech service for reading out text')
param useSpeechOutputAzure bool = false
@description('Show options to use vector embeddings for searching in the app UI')
param useVectors bool = false
@description('Use Built-in integrated Vectorization feature of AI Search to vectorize and ingest documents')
param useIntegratedVectorization bool = false

@description('Enable user document upload feature')
param useUserUpload bool = false
param useLocalPdfParser bool = false
param useLocalHtmlParser bool = false

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

var tenantIdForAuth = !empty(authTenantId) ? authTenantId : tenantId
var authenticationIssuerUri = '${environment().authentication.loginEndpoint}${tenantIdForAuth}/v2.0'

@description('Whether the deployment is running on GitHub Actions')
param runningOnGh string = ''

@description('Whether the deployment is running on Azure DevOps Pipeline')
param runningOnAdo string = ''

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

resource documentIntelligenceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(documentIntelligenceResourceGroupName)) {
  name: !empty(documentIntelligenceResourceGroupName) ? documentIntelligenceResourceGroupName : resourceGroup.name
}

resource computerVisionResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(computerVisionResourceGroupName)) {
  name: !empty(computerVisionResourceGroupName) ? computerVisionResourceGroupName : resourceGroup.name
}

resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : resourceGroup.name
}

resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : resourceGroup.name
}

resource speechResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(speechServiceResourceGroupName)) {
  name: !empty(speechServiceResourceGroupName) ? speechServiceResourceGroupName : resourceGroup.name
}

// Monitor application with Azure Monitor
module monitoring 'core/monitor/monitoring.bicep' = if (useApplicationInsights) {
  name: 'monitoring'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    publicNetworkAccess: publicNetworkAccess
  }
}

module applicationInsightsDashboard 'backend-dashboard.bicep' = if (useApplicationInsights) {
  name: 'application-insights-dashboard'
  scope: resourceGroup
  params: {
    name: !empty(applicationInsightsDashboardName) ? applicationInsightsDashboardName : '${abbrs.portalDashboards}${resourceToken}'
    location: location
    applicationInsightsName: useApplicationInsights ? monitoring.outputs.applicationInsightsName : ''
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
      name: appServiceSkuName
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
    virtualNetworkSubnetId: isolation.outputs.appSubnetId
    publicNetworkAccess: publicNetworkAccess
    allowedOrigins: [ allowedOrigin ]
    clientAppId: clientAppId
    serverAppId: serverAppId
    enableUnauthenticatedAccess: enableUnauthenticatedAccess
    clientSecretSettingName: !empty(clientAppSecret) ? 'AZURE_CLIENT_APP_SECRET' : ''
    authenticationIssuerUri: authenticationIssuerUri
    use32BitWorkerProcess: appServiceSkuName == 'F1'
    alwaysOn: appServiceSkuName != 'F1'
    appSettings: {
      AZURE_STORAGE_ACCOUNT: storage.outputs.name
      AZURE_STORAGE_CONTAINER: storageContainerName
      AZURE_SEARCH_INDEX: searchIndexName
      AZURE_SEARCH_SERVICE: searchService.outputs.name
      AZURE_SEARCH_SEMANTIC_RANKER: actualSearchServiceSemanticRankerLevel
      AZURE_VISION_ENDPOINT: useGPT4V ? computerVision.outputs.endpoint : ''
      AZURE_SEARCH_QUERY_LANGUAGE: searchQueryLanguage
      AZURE_SEARCH_QUERY_SPELLER: searchQuerySpeller
      APPLICATIONINSIGHTS_CONNECTION_STRING: useApplicationInsights ? monitoring.outputs.applicationInsightsConnectionString : ''
      AZURE_SPEECH_SERVICE_ID: useSpeechOutputAzure ? speech.outputs.id : ''
      AZURE_SPEECH_SERVICE_LOCATION: useSpeechOutputAzure ? speech.outputs.location : ''
      USE_SPEECH_INPUT_BROWSER: useSpeechInputBrowser
      USE_SPEECH_OUTPUT_BROWSER: useSpeechOutputBrowser
      USE_SPEECH_OUTPUT_AZURE: useSpeechOutputAzure
      // Shared by all OpenAI deployments
      OPENAI_HOST: openAiHost
      AZURE_OPENAI_EMB_MODEL_NAME: embedding.modelName
      AZURE_OPENAI_EMB_DIMENSIONS: embedding.dimensions
      AZURE_OPENAI_CHATGPT_MODEL: chatGpt.modelName
      AZURE_OPENAI_GPT4V_MODEL: gpt4vModelName
      // Specific to Azure OpenAI
      AZURE_OPENAI_SERVICE: isAzureOpenAiHost && deployAzureOpenAi ? openAi.outputs.name : ''
      AZURE_OPENAI_CHATGPT_DEPLOYMENT: chatGpt.deploymentName
      AZURE_OPENAI_EMB_DEPLOYMENT: embedding.deploymentName
      AZURE_OPENAI_GPT4V_DEPLOYMENT: useGPT4V ? gpt4vDeploymentName : ''
      AZURE_OPENAI_API_VERSION: azureOpenAiApiVersion
      AZURE_OPENAI_API_KEY: azureOpenAiApiKey
      AZURE_OPENAI_CUSTOM_URL: azureOpenAiCustomUrl
      // Used only with non-Azure OpenAI deployments
      OPENAI_API_KEY: openAiApiKey
      OPENAI_ORGANIZATION: openAiApiOrganization
      // Optional login and document level access control system
      AZURE_USE_AUTHENTICATION: useAuthentication
      AZURE_ENFORCE_ACCESS_CONTROL: enforceAccessControl
      AZURE_ENABLE_GLOBAL_DOCUMENTS_ACCESS: enableGlobalDocuments
      AZURE_ENABLE_UNAUTHENTICATED_ACCESS: enableUnauthenticatedAccess
      AZURE_SERVER_APP_ID: serverAppId
      AZURE_SERVER_APP_SECRET: serverAppSecret
      AZURE_CLIENT_APP_ID: clientAppId
      AZURE_CLIENT_APP_SECRET: clientAppSecret
      AZURE_TENANT_ID: tenantId
      AZURE_AUTH_TENANT_ID: tenantIdForAuth
      AZURE_AUTHENTICATION_ISSUER_URI: authenticationIssuerUri
      // CORS support, for frontends on other hosts
      ALLOWED_ORIGIN: allowedOrigin
      USE_VECTORS: useVectors
      USE_GPT4V: useGPT4V
      USE_USER_UPLOAD: useUserUpload
      AZURE_USERSTORAGE_ACCOUNT: useUserUpload ? userStorage.outputs.name : ''
      AZURE_USERSTORAGE_CONTAINER: useUserUpload ? userStorageContainerName : ''
      AZURE_DOCUMENTINTELLIGENCE_SERVICE: documentIntelligence.outputs.name
      USE_LOCAL_PDF_PARSER: useLocalPdfParser
      USE_LOCAL_HTML_PARSER: useLocalHtmlParser
    }
  }
}

var defaultOpenAiDeployments = [
  {
    name: chatGpt.deploymentName
    model: {
      format: 'OpenAI'
      name: chatGpt.modelName
      version: chatGpt.deploymentVersion
    }
    sku: {
      name: 'Standard'
      capacity: chatGpt.deploymentCapacity
    }
  }
  {
    name: embedding.deploymentName
    model: {
      format: 'OpenAI'
      name: embedding.modelName
      version: embedding.deploymentVersion
    }
    sku: {
      name: 'Standard'
      capacity: embedding.deploymentCapacity
    }
  }
]

var openAiDeployments = concat(defaultOpenAiDeployments, useGPT4V ? [
    {
      name: gpt4vDeploymentName
      model: {
        format: 'OpenAI'
        name: gpt4vModelName
        version: gpt4vModelVersion
      }
      sku: {
        name: 'Standard'
        capacity: gpt4vDeploymentCapacity
      }
    }
  ] : [])

module openAi 'core/ai/cognitiveservices.bicep' = if (isAzureOpenAiHost && deployAzureOpenAi) {
  name: 'openai'
  scope: openAiResourceGroup
  params: {
    name: !empty(openAiServiceName) ? openAiServiceName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    location: openAiResourceGroupLocation
    tags: tags
    publicNetworkAccess: publicNetworkAccess
    bypass: bypass
    sku: {
      name: openAiSkuName
    }
    deployments: openAiDeployments
    disableLocalAuth: true
  }
}

// Formerly known as Form Recognizer
// Does not support bypass
module documentIntelligence 'core/ai/cognitiveservices.bicep' = {
  name: 'documentintelligence'
  scope: documentIntelligenceResourceGroup
  params: {
    name: !empty(documentIntelligenceServiceName) ? documentIntelligenceServiceName : '${abbrs.cognitiveServicesDocumentIntelligence}${resourceToken}'
    kind: 'FormRecognizer'
    publicNetworkAccess: publicNetworkAccess
    location: documentIntelligenceResourceGroupLocation
    disableLocalAuth: true
    tags: tags
    sku: {
      name: documentIntelligenceSkuName
    }
  }
}

module computerVision 'core/ai/cognitiveservices.bicep' = if (useGPT4V) {
  name: 'computerVision'
  scope: computerVisionResourceGroup
  params: {
    name: !empty(computerVisionServiceName)
      ? computerVisionServiceName
      : '${abbrs.cognitiveServicesComputerVision}${resourceToken}'
    kind: 'ComputerVision'
    location: computerVisionResourceGroupLocation
    tags: tags
    bypass: bypass
    sku: {
      name: computerVisionSkuName
    }
  }
}

module speech 'core/ai/cognitiveservices.bicep' = if (useSpeechOutputAzure) {
  name: 'speech-service'
  scope: speechResourceGroup
  params: {
    name: !empty(speechServiceName) ? speechServiceName : '${abbrs.cognitiveServicesSpeech}${resourceToken}'
    kind: 'SpeechServices'
    location: !empty(speechServiceLocation) ? speechServiceLocation : location
    tags: tags
    sku: {
      name: speechServiceSkuName
    }
  }
}
module searchService 'core/search/search-services.bicep' = {
  name: 'search-service'
  scope: searchServiceResourceGroup
  params: {
    name: !empty(searchServiceName) ? searchServiceName : 'gptkb-${resourceToken}'
    location: !empty(searchServiceLocation) ? searchServiceLocation : location
    tags: tags
    disableLocalAuth: true
    sku: {
      name: searchServiceSkuName
    }
    semanticSearch: actualSearchServiceSemanticRankerLevel
    publicNetworkAccess: publicNetworkAccess == 'Enabled' ? 'enabled' : (publicNetworkAccess == 'Disabled' ? 'disabled' : null)
    sharedPrivateLinkStorageAccounts: usePrivateEndpoint ? [ storage.outputs.id ] : []
  }
}

module searchDiagnostics 'core/search/search-diagnostics.bicep' = if (useApplicationInsights) {
  name: 'search-diagnostics'
  scope: searchServiceResourceGroup
  params: {
    searchServiceName: searchService.outputs.name
    workspaceId: useApplicationInsights ? monitoring.outputs.logAnalyticsWorkspaceId : ''
  }
}

module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: storageResourceGroup
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: storageResourceGroupLocation
    tags: tags
    publicNetworkAccess: publicNetworkAccess
    bypass: bypass
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
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

module userStorage 'core/storage/storage-account.bicep' = if (useUserUpload) {
  name: 'user-storage'
  scope: storageResourceGroup
  params: {
    name: !empty(userStorageAccountName) ? userStorageAccountName : 'user${abbrs.storageStorageAccounts}${resourceToken}'
    location: storageResourceGroupLocation
    tags: tags
    publicNetworkAccess: publicNetworkAccess
    bypass: bypass
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    isHnsEnabled: true
    sku: {
      name: storageSkuName
    }
    containers: [
      {
        name: userStorageContainerName
        publicAccess: 'None'
      }
    ]
  }
}

// USER ROLES
var principalType = empty(runningOnGh) && empty(runningOnAdo) ? 'User' : 'ServicePrincipal'

module openAiRoleUser 'core/security/role.bicep' = if (isAzureOpenAiHost && deployAzureOpenAi) {
  scope: openAiResourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: principalType
  }
}

// For both document intelligence and computer vision
module cognitiveServicesRoleUser 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'cognitiveservices-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: principalType
  }
}

module speechRoleUser 'core/security/role.bicep' = {
  scope: speechResourceGroup
  name: 'speech-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'f2dc8367-1007-4938-bd23-fe263f013447'
    principalType: principalType
  }
}

module storageRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: principalType
  }
}

module storageContribRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    principalType: principalType
  }
}

module storageOwnerRoleUser 'core/security/role.bicep' = if (useUserUpload) {
  scope: storageResourceGroup
  name: 'storage-owner-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
    principalType: principalType
  }
}

module searchRoleUser 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: principalType
  }
}

module searchContribRoleUser 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: principalType
  }
}

module searchSvcContribRoleUser 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-svccontrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
    principalType: principalType
  }
}

// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = if (isAzureOpenAiHost && deployAzureOpenAi) {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module openAiRoleSearchService 'core/security/role.bicep' = if (isAzureOpenAiHost && deployAzureOpenAi && useIntegratedVectorization) {
  scope: openAiResourceGroup
  name: 'openai-role-searchservice'
  params: {
    principalId: searchService.outputs.principalId
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

module storageOwnerRoleBackend 'core/security/role.bicep' = if (useUserUpload) {
  scope: storageResourceGroup
  name: 'storage-owner-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleSearchService 'core/security/role.bicep' = if (useIntegratedVectorization) {
  scope: storageResourceGroup
  name: 'storage-role-searchservice'
  params: {
    principalId: searchService.outputs.principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'ServicePrincipal'
  }
}

// Used to issue search queries
// https://learn.microsoft.com/azure/search/search-security-rbac
module searchRoleBackend 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

module speechRoleBackend 'core/security/role.bicep' = {
  scope: speechResourceGroup
  name: 'speech-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'f2dc8367-1007-4938-bd23-fe263f013447'
    principalType: 'ServicePrincipal'
  }
}

module isolation 'network-isolation.bicep' = {
  name: 'networks'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    resourceToken: resourceToken
    vnetName: '${abbrs.virtualNetworks}${resourceToken}'
    appServicePlanName: appServicePlan.outputs.name
    provisionVm: provisionVm
    usePrivateEndpoint: usePrivateEndpoint
  }
}

var environmentData = environment()
var privateEndpointConnections = usePrivateEndpoint ? [
  {
    groupId: 'blob'
    dnsZoneName: 'privatelink.blob.${environmentData.suffixes.storage}'
    resourceIds: concat(
      [ storage.outputs.id ],
      useUserUpload ? [ userStorage.outputs.id ] : []
    )
  }
  {
    groupId: 'account'
    dnsZoneName: 'privatelink.openai.azure.com'
    resourceIds: concat(
      [ openAi.outputs.id ],
      useGPT4V ? [ computerVision.outputs.id ] : [],
      !useLocalPdfParser ? [ documentIntelligence.outputs.id ] : []
    )
  }
  {
    groupId: 'searchService'
    dnsZoneName: 'privatelink.search.windows.net'
    resourceIds: [ searchService.outputs.id ]
  }
  {
    groupId: 'sites'
    dnsZoneName: 'privatelink.azurewebsites.net'
    resourceIds: [ backend.outputs.id ]
  }
] : []

module privateEndpoints 'private-endpoints.bicep' = if (usePrivateEndpoint) {
  name: 'privateEndpoints'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    resourceToken: resourceToken
    privateEndpointConnections: privateEndpointConnections
    applicationInsightsId: useApplicationInsights ? monitoring.outputs.applicationInsightsId : ''
    logAnalyticsWorkspaceId: useApplicationInsights ? monitoring.outputs.logAnalyticsWorkspaceId : ''
    vnetName: isolation.outputs.vnetName
    vnetPeSubnetName: isolation.outputs.backendSubnetId
  }
}

module vm 'core/host/vm.bicep' = if (provisionVm && usePrivateEndpoint) {
  name: 'vm'
  scope: resourceGroup
  params: {
    name: '${abbrs.computeVirtualMachines}${resourceToken}'
    location: location
    adminUsername: vmUserName
    adminPassword: vmPassword
    nicId: isolation.outputs.nicId
    osVersion: vmOsVersion
    osPublisher: vmOsPublisher
    osOffer: vmOsOffer
    vmSize: vmSize
  }
}

// Used to read index definitions (required when using authentication)
// https://learn.microsoft.com/azure/search/search-security-rbac
module searchReaderRoleBackend 'core/security/role.bicep' = if (useAuthentication) {
  scope: searchServiceResourceGroup
  name: 'search-reader-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
    principalType: 'ServicePrincipal'
  }
}

// Used to add/remove documents from index (required for user upload feature)
module searchContribRoleBackend 'core/security/role.bicep' = if (useUserUpload) {
  scope: searchServiceResourceGroup
  name: 'search-contrib-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: 'ServicePrincipal'
  }
}

// For computer vision access by the backend
module computerVisionRoleBackend 'core/security/role.bicep' = if (useGPT4V) {
  scope: computerVisionResourceGroup
  name: 'computervision-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

// For document intelligence access by the backend
module documentIntelligenceRoleBackend 'core/security/role.bicep' = if (useUserUpload) {
  scope: documentIntelligenceResourceGroup
  name: 'documentintelligence-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenantId
output AZURE_AUTH_TENANT_ID string = authTenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

// Shared by all OpenAI deployments
output OPENAI_HOST string = openAiHost
output AZURE_OPENAI_EMB_MODEL_NAME string = embedding.modelName
output AZURE_OPENAI_CHATGPT_MODEL string = chatGpt.modelName
output AZURE_OPENAI_GPT4V_MODEL string = gpt4vModelName

// Specific to Azure OpenAI
output AZURE_OPENAI_SERVICE string = isAzureOpenAiHost && deployAzureOpenAi ? openAi.outputs.name : ''
output AZURE_OPENAI_API_VERSION string = isAzureOpenAiHost ? azureOpenAiApiVersion : ''
output AZURE_OPENAI_RESOURCE_GROUP string = isAzureOpenAiHost ? openAiResourceGroup.name : ''
output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = isAzureOpenAiHost ? chatGpt.deploymentName : ''
output AZURE_OPENAI_EMB_DEPLOYMENT string = isAzureOpenAiHost ? embedding.deploymentName : ''
output AZURE_OPENAI_GPT4V_DEPLOYMENT string = isAzureOpenAiHost ? gpt4vDeploymentName : ''

output AZURE_SPEECH_SERVICE_ID string = useSpeechOutputAzure ? speech.outputs.id : ''
output AZURE_SPEECH_SERVICE_LOCATION string = useSpeechOutputAzure ? speech.outputs.location : ''

output AZURE_VISION_ENDPOINT string = useGPT4V ? computerVision.outputs.endpoint : ''

output AZURE_DOCUMENTINTELLIGENCE_SERVICE string = documentIntelligence.outputs.name
output AZURE_DOCUMENTINTELLIGENCE_RESOURCE_GROUP string = documentIntelligenceResourceGroup.name

output AZURE_SEARCH_INDEX string = searchIndexName
output AZURE_SEARCH_SERVICE string = searchService.outputs.name
output AZURE_SEARCH_SERVICE_RESOURCE_GROUP string = searchServiceResourceGroup.name
output AZURE_SEARCH_SEMANTIC_RANKER string = actualSearchServiceSemanticRankerLevel
output AZURE_SEARCH_SERVICE_ASSIGNED_USERID string = searchService.outputs.principalId

output AZURE_STORAGE_ACCOUNT string = storage.outputs.name
output AZURE_STORAGE_CONTAINER string = storageContainerName
output AZURE_STORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output AZURE_USERSTORAGE_ACCOUNT string = useUserUpload ? userStorage.outputs.name : ''
output AZURE_USERSTORAGE_CONTAINER string = userStorageContainerName
output AZURE_USERSTORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output AZURE_USE_AUTHENTICATION bool = useAuthentication

output BACKEND_URI string = backend.outputs.uri
