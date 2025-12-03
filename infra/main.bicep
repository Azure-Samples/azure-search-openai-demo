targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
// microsoft.insights/components has restricted regions
@allowed([
  'eastus'
  'southcentralus'
  'northeurope'
  'westeurope'
  'southeastasia'
  'westus2'
  'uksouth'
  'canadacentral'
  'centralindia'
  'japaneast'
  'australiaeast'
  'koreacentral'
  'francecentral'
  'centralus'
  'eastus2'
  'eastasia'
  'westus'
  'southafricanorth'
  'northcentralus'
  'brazilsouth'
  'switzerlandnorth'
  'norwayeast'
  'norwaywest'
  'australiasoutheast'
  'australiacentral2'
  'germanywestcentral'
  'switzerlandwest'
  'uaecentral'
  'ukwest'
  'japanwest'
  'brazilsoutheast'
  'uaenorth'
  'australiacentral'
  'southindia'
  'westus3'
  'koreasouth'
  'swedencentral'
  'canadaeast'
  'jioindiacentral'
  'jioindiawest'
  'qatarcentral'
  'southafricawest'
  'germanynorth'
  'polandcentral'
  'israelcentral'
  'italynorth'
  'mexicocentral'
  'spaincentral'
  'newzealandnorth'
  'chilecentral'
  'indonesiacentral'
  'malaysiawest'
])
@metadata({
  azd: {
    type: 'location'
  }
})
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
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
param searchServiceSkuName string // Set in main.parameters.json
param searchIndexName string // Set in main.parameters.json
param knowledgeBaseName string = useAgenticKnowledgeBase ? '${searchIndexName}-agent-upgrade' : ''
param searchQueryLanguage string // Set in main.parameters.json
param searchQuerySpeller string // Set in main.parameters.json
param searchServiceSemanticRankerLevel string // Set in main.parameters.json
param searchFieldNameEmbedding string // Set in main.parameters.json
var actualSearchServiceSemanticRankerLevel = (searchServiceSkuName == 'free')
  ? 'disabled'
  : searchServiceSemanticRankerLevel
param searchServiceQueryRewriting string // Set in main.parameters.json
param storageAccountName string = '' // Set in main.parameters.json
param storageResourceGroupName string = '' // Set in main.parameters.json
param storageResourceGroupLocation string = location
param storageContainerName string = 'content'
param storageSkuName string // Set in main.parameters.json

param defaultReasoningEffort string // Set in main.parameters.json
@description('Controls the default retrieval reasoning effort for agentic retrieval (minimal, low, or medium).')
param defaultRetrievalReasoningEffort string = 'minimal'
param useAgenticKnowledgeBase bool // Set in main.parameters.json

param userStorageAccountName string = ''
param userStorageContainerName string = 'user-content'

param tokenStorageContainerName string = 'tokens'

param imageStorageContainerName string = 'images'

param appServiceSkuName string // Set in main.parameters.json

@allowed(['azure', 'openai', 'azure_custom'])
param openAiHost string // Set in main.parameters.json
param isAzureOpenAiHost bool = startsWith(openAiHost, 'azure')
param deployAzureOpenAi bool = openAiHost == 'azure'
param azureOpenAiCustomUrl string = ''
@secure()
param azureOpenAiApiKey string = ''
param azureOpenAiDisableKeys bool = true
param openAiServiceName string = ''
param openAiResourceGroupName string = ''

param speechServiceResourceGroupName string = ''
param speechServiceLocation string = ''
param speechServiceName string = ''
param speechServiceSkuName string // Set in main.parameters.json
param speechServiceVoice string = ''
param useMultimodal bool = false
param useEval bool = false
param useCloudIngestion bool = false

@allowed(['free', 'provisioned', 'serverless'])
param cosmosDbSkuName string // Set in main.parameters.json
param cosmodDbResourceGroupName string = ''
param cosmosDbLocation string = ''
param cosmosDbAccountName string = ''
param cosmosDbThroughput int = 400
param chatHistoryDatabaseName string = 'chat-database'
param chatHistoryContainerName string = 'chat-history-v2'
param chatHistoryVersion string = 'cosmosdb-v2'

// https://learn.microsoft.com/azure/ai-services/openai/concepts/models?tabs=global-standard%2Cstandard-chat-completions#models-by-deployment-type
@description('Location for the OpenAI resource group')
@allowed([
  'australiaeast'
  'brazilsouth'
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'germanywestcentral'
  'japaneast'
  'koreacentral'
  'northcentralus'
  'norwayeast'
  'polandcentral'
  'southafricanorth'
  'southcentralus'
  'southindia'
  'spaincentral'
  'swedencentral'
  'switzerlandnorth'
  'uaenorth'
  'uksouth'
  'westeurope'
  'westus'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param openAiLocation string

param openAiSkuName string = 'S0'

@secure()
param openAiApiKey string = ''
param openAiApiOrganization string = ''

param documentIntelligenceServiceName string = '' // Set in main.parameters.json
param documentIntelligenceResourceGroupName string = '' // Set in main.parameters.json

// Limited regions for new version:
// https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-layout
@description('Location for the Document Intelligence resource group')
@allowed(['eastus', 'westus2', 'westeurope', 'australiaeast'])
@metadata({
  azd: {
    type: 'location'
  }
})
param documentIntelligenceResourceGroupLocation string

param documentIntelligenceSkuName string // Set in main.parameters.json

param visionServiceName string = '' // Set in main.parameters.json
param visionResourceGroupName string = '' // Set in main.parameters.json
param visionResourceGroupLocation string = '' // Set in main.parameters.json

param contentUnderstandingServiceName string = '' // Set in main.parameters.json
param contentUnderstandingResourceGroupName string = '' // Set in main.parameters.json

param chatGptModelName string = ''
param chatGptDeploymentName string = ''
param chatGptDeploymentVersion string = ''
param chatGptDeploymentSkuName string = ''
param chatGptDeploymentCapacity int = 0

var chatGpt = {
  modelName: !empty(chatGptModelName) ? chatGptModelName : 'gpt-4.1-mini'
  deploymentName: !empty(chatGptDeploymentName) ? chatGptDeploymentName : 'gpt-4.1-mini'
  deploymentVersion: !empty(chatGptDeploymentVersion) ? chatGptDeploymentVersion : '2025-04-14'
  deploymentSkuName: !empty(chatGptDeploymentSkuName) ? chatGptDeploymentSkuName : 'GlobalStandard'
  deploymentCapacity: chatGptDeploymentCapacity != 0 ? chatGptDeploymentCapacity : 30
}

param embeddingModelName string = ''
param embeddingDeploymentName string = ''
param embeddingDeploymentVersion string = ''
param embeddingDeploymentSkuName string = ''
param embeddingDeploymentCapacity int = 0
param embeddingDimensions int = 0
var embedding = {
  modelName: !empty(embeddingModelName) ? embeddingModelName : 'text-embedding-3-large'
  deploymentName: !empty(embeddingDeploymentName) ? embeddingDeploymentName : 'text-embedding-3-large'
  deploymentVersion: !empty(embeddingDeploymentVersion) ? embeddingDeploymentVersion : (embeddingModelName == 'text-embedding-ada-002' ? '2' : '1')
  deploymentSkuName: !empty(embeddingDeploymentSkuName) ? embeddingDeploymentSkuName : (embeddingModelName == 'text-embedding-ada-002' ? 'Standard' : 'GlobalStandard')
  deploymentCapacity: embeddingDeploymentCapacity != 0 ? embeddingDeploymentCapacity : 200
  dimensions: embeddingDimensions != 0 ? embeddingDimensions : 3072
}

param evalModelName string = ''
param evalDeploymentName string = ''
param evalModelVersion string = ''
param evalDeploymentSkuName string = ''
param evalDeploymentCapacity int = 0
var eval = {
  modelName: !empty(evalModelName) ? evalModelName : 'gpt-4o'
  deploymentName: !empty(evalDeploymentName) ? evalDeploymentName : 'eval'
  deploymentVersion: !empty(evalModelVersion) ? evalModelVersion : '2024-08-06'
  deploymentSkuName: !empty(evalDeploymentSkuName) ? evalDeploymentSkuName : 'GlobalStandard' // Not backward-compatible
  deploymentCapacity: evalDeploymentCapacity != 0 ? evalDeploymentCapacity : 30
}

param knowledgeBaseModelName string = ''
param knowledgeBaseDeploymentName string = ''
param knowledgeBaseModelVersion string = ''
param knowledgeBaseDeploymentSkuName string = ''
param knowledgeBaseDeploymentCapacity int = 0
var knowledgeBase = {
  modelName: !empty(knowledgeBaseModelName) ? knowledgeBaseModelName : 'gpt-4.1-mini'
  deploymentName: !empty(knowledgeBaseDeploymentName) ? knowledgeBaseDeploymentName : 'knowledgebase'
  deploymentVersion: !empty(knowledgeBaseModelVersion) ? knowledgeBaseModelVersion : '2025-04-14'
  deploymentSkuName: !empty(knowledgeBaseDeploymentSkuName) ? knowledgeBaseDeploymentSkuName : 'GlobalStandard'
  deploymentCapacity: knowledgeBaseDeploymentCapacity != 0 ? knowledgeBaseDeploymentCapacity : 100
}


param tenantId string = tenant().tenantId
param authTenantId string = ''

// Used for the optional login and document level access control system
param useAuthentication bool = false
param enforceAccessControl bool = false
// Force using MSAL app authentication instead of built-in App Service authentication
// https://learn.microsoft.com/azure/app-service/overview-authentication-authorization
param disableAppServicesAuthentication bool = false
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

@allowed(['None', 'AzureServices'])
@description('If allowedIp is set, whether azure services are allowed to bypass the storage and AI services firewall.')
param bypass string = 'AzureServices'

@description('Public network access value for all deployed resources')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Add a private endpoints for network connectivity')
param usePrivateEndpoint bool = false

@description('Use a P2S VPN Gateway for secure access to the private endpoints')
param useVpnGateway bool = false

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Use Application Insights for monitoring and performance tracing')
param useApplicationInsights bool = false

@description('Enable language picker')
param enableLanguagePicker bool = false
@description('Use speech recognition feature in browser')
param useSpeechInputBrowser bool = false
@description('Use speech synthesis in browser')
param useSpeechOutputBrowser bool = false
@description('Use Azure speech service for reading out text')
param useSpeechOutputAzure bool = false
@description('Use chat history feature in browser')
param useChatHistoryBrowser bool = false
@description('Use chat history feature in CosmosDB')
param useChatHistoryCosmos bool = false
@description('Show options to use vector embeddings for searching in the app UI')
param useVectors bool = false
@description('Use Built-in integrated Vectorization feature of AI Search to vectorize and ingest documents')
param useIntegratedVectorization bool = false

@description('Use media description feature with Azure Content Understanding during ingestion')
param useMediaDescriberAzureCU bool = true

@description('Enable user document upload feature')
param useUserUpload bool = false
param useLocalPdfParser bool = false
param useLocalHtmlParser bool = false

@description('Use AI project')
param useAiProject bool = false

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

var tenantIdForAuth = !empty(authTenantId) ? authTenantId : tenantId
var authenticationIssuerUri = '${environment().authentication.loginEndpoint}${tenantIdForAuth}/v2.0'

@description('Whether the deployment is running on GitHub Actions')
param runningOnGh string = ''

@description('Whether the deployment is running on Azure DevOps Pipeline')
param runningOnAdo string = ''

@description('Used by azd for containerapps deployment')
param webAppExists bool

@allowed(['Consumption', 'D4', 'D8', 'D16', 'D32', 'E4', 'E8', 'E16', 'E32', 'NC24-A100', 'NC48-A100', 'NC96-A100'])
param azureContainerAppsWorkloadProfile string

@allowed(['appservice', 'containerapps'])
param deploymentTarget string = 'appservice'

// RAG Configuration Parameters
@description('Whether to use text embeddings for RAG search')
param ragSearchTextEmbeddings bool = true
@description('Whether to use image embeddings for RAG search')
param ragSearchImageEmbeddings bool = true
@description('Whether to send text sources to LLM for RAG responses')
param ragSendTextSources bool = true
@description('Whether to send image sources to LLM for RAG responses')
param ragSendImageSources bool = true
@description('Whether to enable web sources for agentic retrieval')
param useWebSource bool = false
@description('Whether to enable SharePoint sources for agentic retrieval')
param useSharePointSource bool = false

param acaIdentityName string = deploymentTarget == 'containerapps' ? '${environmentName}-aca-identity' : ''
param acaManagedEnvironmentName string = deploymentTarget == 'containerapps' ? '${environmentName}-aca-env' : ''
param containerRegistryName string = deploymentTarget == 'containerapps'
  ? '${replace(toLower(environmentName), '-', '')}acr'
  : ''

// Configure CORS for allowing different web apps to use the backend
// For more information please see https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
var msftAllowedOrigins = [ 'https://portal.azure.com', 'https://ms.portal.azure.com' ]
var loginEndpoint = environment().authentication.loginEndpoint
var loginEndpointFixed = lastIndexOf(loginEndpoint, '/') == length(loginEndpoint) - 1 ? substring(loginEndpoint, 0, max(length(loginEndpoint) - 1, 0)) : loginEndpoint
var allMsftAllowedOrigins = !(empty(clientAppId)) ? union(msftAllowedOrigins, [ loginEndpointFixed ]) : msftAllowedOrigins
// Combine custom origins with Microsoft origins, remove any empty origin strings and remove any duplicate origins
var allowedOrigins = reduce(filter(union(split(allowedOrigin, ';'), allMsftAllowedOrigins), o => length(trim(o)) > 0), [], (cur, next) => union(cur, [next]))

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

resource documentIntelligenceResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(documentIntelligenceResourceGroupName)) {
  name: !empty(documentIntelligenceResourceGroupName) ? documentIntelligenceResourceGroupName : resourceGroup.name
}

resource visionResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(visionResourceGroupName)) {
  name: !empty(visionResourceGroupName) ? visionResourceGroupName : resourceGroup.name
}

resource contentUnderstandingResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(contentUnderstandingResourceGroupName)) {
  name: !empty(contentUnderstandingResourceGroupName) ? contentUnderstandingResourceGroupName : resourceGroup.name
}

resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : resourceGroup.name
}

resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : resourceGroup.name
}

resource speechResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(speechServiceResourceGroupName)) {
  name: !empty(speechServiceResourceGroupName) ? speechServiceResourceGroupName : resourceGroup.name
}

resource cosmosDbResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = if (!empty(cosmodDbResourceGroupName)) {
  name: !empty(cosmodDbResourceGroupName) ? cosmodDbResourceGroupName : resourceGroup.name
}

// Monitor application with Azure Monitor
module monitoring 'core/monitor/monitoring.bicep' = if (useApplicationInsights) {
  name: 'monitoring'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    applicationInsightsName: !empty(applicationInsightsName)
      ? applicationInsightsName
      : '${abbrs.insightsComponents}${resourceToken}'
    logAnalyticsName: !empty(logAnalyticsName)
      ? logAnalyticsName
      : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    publicNetworkAccess: publicNetworkAccess
  }
}

module applicationInsightsDashboard 'backend-dashboard.bicep' = if (useApplicationInsights) {
  name: 'application-insights-dashboard'
  scope: resourceGroup
  params: {
    name: !empty(applicationInsightsDashboardName)
      ? applicationInsightsDashboardName
      : '${abbrs.portalDashboards}${resourceToken}'
    location: location
    applicationInsightsName: useApplicationInsights ? monitoring!.outputs.applicationInsightsName : ''
  }
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan 'core/host/appserviceplan.bicep' = if (deploymentTarget == 'appservice') {
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

var appEnvVariables = {
  AZURE_STORAGE_ACCOUNT: storage.outputs.name
  AZURE_STORAGE_CONTAINER: storageContainerName
  AZURE_SEARCH_INDEX: searchIndexName
  AZURE_SEARCH_KNOWLEDGEBASE_NAME: knowledgeBaseName
  AZURE_SEARCH_SERVICE: searchService.outputs.name
  AZURE_SEARCH_SEMANTIC_RANKER: actualSearchServiceSemanticRankerLevel
  AZURE_SEARCH_QUERY_REWRITING: searchServiceQueryRewriting
  AZURE_VISION_ENDPOINT: useMultimodal ? vision!.outputs.endpoint : ''
  AZURE_SEARCH_QUERY_LANGUAGE: searchQueryLanguage
  AZURE_SEARCH_QUERY_SPELLER: searchQuerySpeller
  AZURE_SEARCH_FIELD_NAME_EMBEDDING: searchFieldNameEmbedding
  APPLICATIONINSIGHTS_CONNECTION_STRING: useApplicationInsights
    ? monitoring!.outputs.applicationInsightsConnectionString
    : ''
  AZURE_SPEECH_SERVICE_ID: useSpeechOutputAzure ? speech!.outputs.resourceId : ''
  AZURE_SPEECH_SERVICE_LOCATION: useSpeechOutputAzure ? speech!.outputs.location : ''
  AZURE_SPEECH_SERVICE_VOICE: useSpeechOutputAzure ? speechServiceVoice : ''
  ENABLE_LANGUAGE_PICKER: enableLanguagePicker
  USE_SPEECH_INPUT_BROWSER: useSpeechInputBrowser
  USE_SPEECH_OUTPUT_BROWSER: useSpeechOutputBrowser
  USE_SPEECH_OUTPUT_AZURE: useSpeechOutputAzure
  USE_AGENTIC_KNOWLEDGEBASE: useAgenticKnowledgeBase
  // Chat history settings
  USE_CHAT_HISTORY_BROWSER: useChatHistoryBrowser
  USE_CHAT_HISTORY_COSMOS: useChatHistoryCosmos
  AZURE_COSMOSDB_ACCOUNT: (useAuthentication && useChatHistoryCosmos) ? cosmosDb!.outputs.name : ''
  AZURE_CHAT_HISTORY_DATABASE: chatHistoryDatabaseName
  AZURE_CHAT_HISTORY_CONTAINER: chatHistoryContainerName
  AZURE_CHAT_HISTORY_VERSION: chatHistoryVersion
  // Shared by all OpenAI deployments
  OPENAI_HOST: openAiHost
  AZURE_OPENAI_EMB_MODEL_NAME: embedding.modelName
  AZURE_OPENAI_EMB_DIMENSIONS: embedding.dimensions
  AZURE_OPENAI_CHATGPT_MODEL: chatGpt.modelName
  AZURE_OPENAI_REASONING_EFFORT: defaultReasoningEffort
  AGENTIC_KNOWLEDGEBASE_REASONING_EFFORT: defaultRetrievalReasoningEffort
  // Specific to Azure OpenAI
  AZURE_OPENAI_SERVICE: isAzureOpenAiHost && deployAzureOpenAi ? openAi!.outputs.name : ''
  AZURE_OPENAI_CHATGPT_DEPLOYMENT: chatGpt.deploymentName
  AZURE_OPENAI_EMB_DEPLOYMENT: embedding.deploymentName
  AZURE_OPENAI_knowledgeBase_MODEL: knowledgeBase.modelName
  AZURE_OPENAI_knowledgeBase_DEPLOYMENT: knowledgeBase.deploymentName
  AZURE_OPENAI_API_KEY_OVERRIDE: azureOpenAiApiKey
  AZURE_OPENAI_CUSTOM_URL: azureOpenAiCustomUrl
  // Used only with non-Azure OpenAI deployments
  OPENAI_API_KEY: openAiApiKey
  OPENAI_ORGANIZATION: openAiApiOrganization
  // Optional login and document level access control system
  AZURE_USE_AUTHENTICATION: useAuthentication
  AZURE_ENFORCE_ACCESS_CONTROL: enforceAccessControl
  AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS: enableGlobalDocuments
  AZURE_ENABLE_UNAUTHENTICATED_ACCESS: enableUnauthenticatedAccess
  AZURE_SERVER_APP_ID: serverAppId
  AZURE_CLIENT_APP_ID: clientAppId
  AZURE_TENANT_ID: tenantId
  AZURE_AUTH_TENANT_ID: tenantIdForAuth
  AZURE_AUTHENTICATION_ISSUER_URI: authenticationIssuerUri
  // CORS support, for frontends on other hosts
  ALLOWED_ORIGIN: join(allowedOrigins, ';')
  USE_VECTORS: useVectors
  USE_MULTIMODAL: useMultimodal
  USE_USER_UPLOAD: useUserUpload
  AZURE_USERSTORAGE_ACCOUNT: useUserUpload ? userStorage!.outputs.name : ''
  AZURE_USERSTORAGE_CONTAINER: useUserUpload ? userStorageContainerName : ''
  AZURE_IMAGESTORAGE_CONTAINER: useMultimodal ? imageStorageContainerName : ''
  AZURE_DOCUMENTINTELLIGENCE_SERVICE: documentIntelligence.outputs.name
  USE_LOCAL_PDF_PARSER: useLocalPdfParser
  USE_LOCAL_HTML_PARSER: useLocalHtmlParser
  USE_MEDIA_DESCRIBER_AZURE_CU: useMediaDescriberAzureCU
  AZURE_CONTENTUNDERSTANDING_ENDPOINT: useMediaDescriberAzureCU ? contentUnderstanding!.outputs.endpoint : ''
  RUNNING_IN_PRODUCTION: 'true'
  // RAG Configuration
  RAG_SEARCH_TEXT_EMBEDDINGS: ragSearchTextEmbeddings
  RAG_SEARCH_IMAGE_EMBEDDINGS: ragSearchImageEmbeddings
  RAG_SEND_TEXT_SOURCES: ragSendTextSources
  RAG_SEND_IMAGE_SOURCES: ragSendImageSources
  USE_WEB_SOURCE: useWebSource
  USE_SHAREPOINT_SOURCE: useSharePointSource
}

// App Service for the web application (Python Quart app with JS frontend)
module backend 'core/host/appservice.bicep' = if (deploymentTarget == 'appservice') {
  name: 'web'
  scope: resourceGroup
  params: {
    name: !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    // Need to check deploymentTarget again due to https://github.com/Azure/bicep/issues/3990
    appServicePlanId: deploymentTarget == 'appservice' ? appServicePlan!.outputs.id : ''
    runtimeName: 'python'
    runtimeVersion: '3.11'
    appCommandLine: 'python3 -m gunicorn main:app'
    scmDoBuildDuringDeployment: true
    managedIdentity: true
    virtualNetworkSubnetId: usePrivateEndpoint ? isolation!.outputs.appSubnetId : ''
    publicNetworkAccess: publicNetworkAccess
    allowedOrigins: allowedOrigins
    clientAppId: clientAppId
    serverAppId: serverAppId
    enableUnauthenticatedAccess: enableUnauthenticatedAccess
    disableAppServicesAuthentication: disableAppServicesAuthentication
    clientSecretSettingName: !empty(clientAppSecret) ? 'AZURE_CLIENT_APP_SECRET' : ''
    authenticationIssuerUri: authenticationIssuerUri
    use32BitWorkerProcess: appServiceSkuName == 'F1'
    alwaysOn: appServiceSkuName != 'F1'
    appSettings: union(appEnvVariables, {
      AZURE_SERVER_APP_SECRET: serverAppSecret
      AZURE_CLIENT_APP_SECRET: clientAppSecret
    })
  }
}

// Azure container apps resources (Only deployed if deploymentTarget is 'containerapps')

// User-assigned identity for pulling images from ACR
module acaIdentity 'core/security/aca-identity.bicep' = if (deploymentTarget == 'containerapps') {
  name: 'aca-identity'
  scope: resourceGroup
  params: {
    identityName: acaIdentityName
    location: location
  }
}

module containerApps 'core/host/container-apps.bicep' = if (deploymentTarget == 'containerapps') {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    tags: tags
    location: location
    containerAppsEnvironmentName: acaManagedEnvironmentName
    containerRegistryName: '${containerRegistryName}${resourceToken}'
    logAnalyticsWorkspaceName: useApplicationInsights ? monitoring!.outputs.logAnalyticsWorkspaceName : ''
    subnetResourceId: usePrivateEndpoint ? isolation!.outputs.appSubnetId : ''
    usePrivateIngress: usePrivateEndpoint
    workloadProfile: azureContainerAppsWorkloadProfile
  }
}

// Container Apps for the web application (Python Quart app with JS frontend)
module acaBackend 'core/host/container-app-upsert.bicep' = if (deploymentTarget == 'containerapps') {
  name: 'aca-web'
  scope: resourceGroup
  params: {
    name: !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesContainerApps}backend-${resourceToken}'
    location: location
    identityName: (deploymentTarget == 'containerapps') ? acaIdentityName : ''
    exists: webAppExists
    containerRegistryName: (deploymentTarget == 'containerapps') ? containerApps!.outputs.registryName : ''
    containerAppsEnvironmentName: (deploymentTarget == 'containerapps') ? containerApps!.outputs.environmentName : ''
    tags: union(tags, { 'azd-service-name': 'backend' })
    targetPort: 8000
    containerCpuCoreCount: '1.0'
    containerMemory: '2Gi'
    containerMinReplicas: usePrivateEndpoint ? 1 : 0
    allowedOrigins: allowedOrigins
    env: union(appEnvVariables, {
      // For using managed identity to access Azure resources. See https://github.com/microsoft/azure-container-apps/issues/442
      AZURE_CLIENT_ID: (deploymentTarget == 'containerapps') ? acaIdentity!.outputs.clientId : ''
    })
    secrets: useAuthentication ? {
      azureclientappsecret: clientAppSecret
      azureserverappsecret: serverAppSecret
    } : {}
    envSecrets: useAuthentication ? [
      {
        name: 'AZURE_CLIENT_APP_SECRET'
        secretRef: 'azureclientappsecret'
      }
      {
        name: 'AZURE_SERVER_APP_SECRET'
        secretRef: 'azureserverappsecret'
      }
    ] : []
  }
}

module acaAuth 'core/host/container-apps-auth.bicep' = if (deploymentTarget == 'containerapps' && !empty(clientAppId)) {
  name: 'aca-auth'
  scope: resourceGroup
  params: {
    name: acaBackend!.outputs.name
    clientAppId: clientAppId
    serverAppId: serverAppId
    clientSecretSettingName: !empty(clientAppSecret) ? 'azureclientappsecret' : ''
    authenticationIssuerUri: authenticationIssuerUri
    enableUnauthenticatedAccess: enableUnauthenticatedAccess
    blobContainerUri: 'https://${storageAccountName}.blob.${environment().suffixes.storage}/${tokenStorageContainerName}'
    appIdentityResourceId: (deploymentTarget == 'appservice') ? '' : acaBackend!.outputs.identityResourceId
  }
}

// Optional Azure Functions for document ingestion and processing
module functions 'app/functions.bicep' = if (useCloudIngestion) {
  name: 'functions'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    applicationInsightsName: useApplicationInsights ? monitoring!.outputs.applicationInsightsName : ''
    storageResourceGroupName: storageResourceGroup.name
    searchServiceResourceGroupName: searchServiceResourceGroup.name
    openAiResourceGroupName: openAiResourceGroup.name
    documentIntelligenceResourceGroupName: documentIntelligenceResourceGroup.name
    visionServiceName: useMultimodal ? vision!.outputs.name : ''
    visionResourceGroupName: useMultimodal ? visionResourceGroup.name : resourceGroup.name
    contentUnderstandingServiceName: useMediaDescriberAzureCU ? contentUnderstanding!.outputs.name : ''
    contentUnderstandingResourceGroupName: useMediaDescriberAzureCU ? contentUnderstandingResourceGroup.name : resourceGroup.name
    documentExtractorName: '${abbrs.webSitesFunctions}doc-extractor-${resourceToken}'
    figureProcessorName: '${abbrs.webSitesFunctions}figure-processor-${resourceToken}'
    textProcessorName: '${abbrs.webSitesFunctions}text-processor-${resourceToken}'
    openIdIssuer: authenticationIssuerUri
    appEnvVariables: appEnvVariables
    searchUserAssignedIdentityClientId: searchService.outputs.userAssignedIdentityClientId
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
      name: chatGpt.deploymentSkuName
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
      name: embedding.deploymentSkuName
      capacity: embedding.deploymentCapacity
    }
  }
]

var openAiDeployments = concat(
  defaultOpenAiDeployments,
  useEval
    ? [
      {
        name: eval.deploymentName
        model: {
          format: 'OpenAI'
          name: eval.modelName
          version: eval.deploymentVersion
        }
        sku: {
          name: eval.deploymentSkuName
          capacity: eval.deploymentCapacity
        }
      }
    ] : [],
  useAgenticKnowledgeBase
    ? [
        {
          name: knowledgeBase.deploymentName
          model: {
            format: 'OpenAI'
            name: knowledgeBase.modelName
            version: knowledgeBase.deploymentVersion
          }
          sku: {
            name: knowledgeBase.deploymentSkuName
            capacity: knowledgeBase.deploymentCapacity
          }
        }
      ]
    : []
)

module openAi 'br/public:avm/res/cognitive-services/account:0.7.2' = if (isAzureOpenAiHost && deployAzureOpenAi) {
  name: 'openai'
  scope: openAiResourceGroup
  params: {
    name: !empty(openAiServiceName) ? openAiServiceName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    location: openAiLocation
    tags: tags
    kind: 'OpenAI'
    customSubDomainName: !empty(openAiServiceName)
      ? openAiServiceName
      : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: 'Allow'
      bypass: bypass
    }
    sku: openAiSkuName
    deployments: openAiDeployments
    disableLocalAuth: azureOpenAiDisableKeys
  }
}

// Formerly known as Form Recognizer
// Does not support bypass
module documentIntelligence 'br/public:avm/res/cognitive-services/account:0.7.2' = {
  name: 'documentintelligence'
  scope: documentIntelligenceResourceGroup
  params: {
    name: !empty(documentIntelligenceServiceName)
      ? documentIntelligenceServiceName
      : '${abbrs.cognitiveServicesDocumentIntelligence}${resourceToken}'
    kind: 'FormRecognizer'
    customSubDomainName: !empty(documentIntelligenceServiceName)
      ? documentIntelligenceServiceName
      : '${abbrs.cognitiveServicesDocumentIntelligence}${resourceToken}'
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: 'Allow'
    }
    location: documentIntelligenceResourceGroupLocation
    disableLocalAuth: true
    tags: tags
    sku: documentIntelligenceSkuName
  }
}

module vision 'br/public:avm/res/cognitive-services/account:0.7.2' = if (useMultimodal) {
  name: 'vision'
  scope: visionResourceGroup
  params: {
    name: !empty(visionServiceName)
      ? visionServiceName
      : '${abbrs.cognitiveServicesVision}${resourceToken}'
    kind: 'CognitiveServices'
    networkAcls: {
      defaultAction: 'Allow'
    }
    customSubDomainName: !empty(visionServiceName)
      ? visionServiceName
      : '${abbrs.cognitiveServicesVision}${resourceToken}'
    location: visionResourceGroupLocation
    tags: tags
    sku: 'S0'
  }
}


module contentUnderstanding 'br/public:avm/res/cognitive-services/account:0.7.2' = if (useMediaDescriberAzureCU) {
  name: 'content-understanding'
  scope: contentUnderstandingResourceGroup
  params: {
    name: !empty(contentUnderstandingServiceName)
      ? contentUnderstandingServiceName
      : '${abbrs.cognitiveServicesContentUnderstanding}${resourceToken}'
    kind: 'AIServices'
    networkAcls: {
      defaultAction: 'Allow'
    }
    customSubDomainName: !empty(contentUnderstandingServiceName)
      ? contentUnderstandingServiceName
      : '${abbrs.cognitiveServicesContentUnderstanding}${resourceToken}'
    // Hard-coding to westus for now, due to limited availability and no overlap with Document Intelligence
    location: 'westus'
    tags: tags
    sku: 'S0'
  }
}

module speech 'br/public:avm/res/cognitive-services/account:0.7.2' = if (useSpeechOutputAzure) {
  name: 'speech-service'
  scope: speechResourceGroup
  params: {
    name: !empty(speechServiceName) ? speechServiceName : '${abbrs.cognitiveServicesSpeech}${resourceToken}'
    kind: 'SpeechServices'
    networkAcls: {
      defaultAction: 'Allow'
    }
    customSubDomainName: !empty(speechServiceName)
      ? speechServiceName
      : '${abbrs.cognitiveServicesSpeech}${resourceToken}'
    location: !empty(speechServiceLocation) ? speechServiceLocation : location
    tags: tags
    sku: speechServiceSkuName
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
    publicNetworkAccess: publicNetworkAccess == 'Enabled'
      ? 'enabled'
      : (publicNetworkAccess == 'Disabled' ? 'disabled' : null)
    sharedPrivateLinkStorageAccounts: (usePrivateEndpoint && useIntegratedVectorization) ? [storage.outputs.id] : []
  }
}

module searchDiagnostics 'core/search/search-diagnostics.bicep' = if (useApplicationInsights) {
  name: 'search-diagnostics'
  scope: searchServiceResourceGroup
  params: {
    searchServiceName: searchService.outputs.name
    workspaceId: useApplicationInsights ? monitoring!.outputs.logAnalyticsWorkspaceId : ''
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
      {
        name: imageStorageContainerName
        publicAccess: 'None'
      }
      {
        name: tokenStorageContainerName
        publicAccess: 'None'
      }
    ]
  }
}

module userStorage 'core/storage/storage-account.bicep' = if (useUserUpload) {
  name: 'user-storage'
  scope: storageResourceGroup
  params: {
    name: !empty(userStorageAccountName)
      ? userStorageAccountName
      : 'user${abbrs.storageStorageAccounts}${resourceToken}'
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

module cosmosDb 'br/public:avm/res/document-db/database-account:0.6.1' = if (useAuthentication && useChatHistoryCosmos) {
  name: 'cosmosdb'
  scope: cosmosDbResourceGroup
  params: {
    name: !empty(cosmosDbAccountName) ? cosmosDbAccountName : '${abbrs.documentDBDatabaseAccounts}${resourceToken}'
    location: !empty(cosmosDbLocation) ? cosmosDbLocation : location
    locations: [
      {
        locationName: !empty(cosmosDbLocation) ? cosmosDbLocation : location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    enableFreeTier: cosmosDbSkuName == 'free'
    capabilitiesToAdd: cosmosDbSkuName == 'serverless' ? ['EnableServerless'] : []
    networkRestrictions: {
      ipRules: []
      networkAclBypass: bypass
      publicNetworkAccess: publicNetworkAccess
      virtualNetworkRules: []
    }
    sqlDatabases: [
      {
        name: chatHistoryDatabaseName
        throughput: (cosmosDbSkuName == 'serverless') ? null : cosmosDbThroughput
        containers: [
          {
            name: chatHistoryContainerName
            kind: 'MultiHash'
            paths: [
              '/entra_oid'
              '/session_id'
            ]
            indexingPolicy: {
              indexingMode: 'consistent'
              automatic: true
              includedPaths: [
                {
                  path: '/entra_oid/?'
                }
                {
                  path: '/session_id/?'
                }
                {
                  path: '/timestamp/?'
                }
                {
                  path: '/type/?'
                }
              ]
              excludedPaths: [
                {
                  path: '/*'
                }
              ]
            }
          }
        ]
      }
    ]
  }
}

module ai 'core/ai/ai-environment.bicep' = if (useAiProject) {
  name: 'ai'
  scope: resourceGroup
  params: {
    // Limited region support: https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk#region-support
    location: 'eastus2'
    tags: tags
    hubName: 'aihub-${resourceToken}'
    projectName: 'aiproj-${resourceToken}'
    storageAccountId: storage.outputs.id
    applicationInsightsId: !useApplicationInsights ? '' : monitoring!.outputs.applicationInsightsId
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

// For both Document Intelligence and AI vision
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
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // Storage Blob Data Reader
    principalType: principalType
  }
}

module storageContribRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: principalType
  }
}

module storageOwnerRoleUser 'core/security/role.bicep' = if (useUserUpload) {
  scope: storageResourceGroup
  name: 'storage-owner-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b' // Storage Blob Data Owner
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

module cosmosDbAccountContribRoleUser 'core/security/role.bicep' = if (useAuthentication && useChatHistoryCosmos) {
  scope: cosmosDbResourceGroup
  name: 'cosmosdb-account-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5bd9cd88-fe45-4216-938b-f97437e15450'
    principalType: principalType
  }
}

// RBAC for Cosmos DB
// https://learn.microsoft.com/azure/cosmos-db/nosql/security/how-to-grant-data-plane-role-based-access
module cosmosDbDataContribRoleUser 'core/security/documentdb-sql-role.bicep' = if (useAuthentication && useChatHistoryCosmos) {
  scope: cosmosDbResourceGroup
  name: 'cosmosdb-data-contrib-role-user'
  params: {
    databaseAccountName: (useAuthentication && useChatHistoryCosmos) ? cosmosDb!.outputs.name : ''
    principalId: principalId
    // Cosmos DB Built-in Data Contributor role
    roleDefinitionId: (useAuthentication && useChatHistoryCosmos)
      ? '/${subscription().id}/resourceGroups/${cosmosDb!.outputs.resourceGroupName}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmosDb!.outputs.name}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
      : ''
  }
}

// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = if (isAzureOpenAiHost && deployAzureOpenAi) {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module openAiRoleSearchService 'core/security/role.bicep' = if (isAzureOpenAiHost && deployAzureOpenAi) {
  scope: openAiResourceGroup
  name: 'openai-role-searchservice'
  params: {
    principalId: searchService.outputs.systemAssignedPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module visionRoleSearchService 'core/security/role.bicep' = if (useMultimodal) {
  scope: visionResourceGroup
  name: 'vision-role-searchservice'
  params: {
    principalId: searchService.outputs.systemAssignedPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleBackend 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // Storage Blob Data Reader
    principalType: 'ServicePrincipal'
  }
}

module storageOwnerRoleBackend 'core/security/role.bicep' = if (useUserUpload) {
  scope: storageResourceGroup
  name: 'storage-owner-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b' // Storage Blob Data Owner
    principalType: 'ServicePrincipal'
  }
}

// Search service needs blob read access for both integrated vectorization and cloud ingestion indexer data source
module storageRoleSearchService 'core/security/role.bicep' = if (useIntegratedVectorization || useCloudIngestion) {
  scope: storageResourceGroup
  name: 'storage-role-searchservice'
  params: {
    principalId: searchService.outputs.systemAssignedPrincipalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // Storage Blob Data Reader
    principalType: 'ServicePrincipal'
  }
}

module storageRoleContributorSearchService 'core/security/role.bicep' = if (useIntegratedVectorization && useMultimodal) {
  scope: storageResourceGroup
  name: 'storage-role-contributor-searchservice'
  params: {
    principalId: searchService.outputs.systemAssignedPrincipalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Necessary for the Container Apps backend to store authentication tokens in the blob storage container
module storageRoleContributorBackend 'core/security/role.bicep' = if (deploymentTarget == 'containerapps' && !empty(clientAppId)) {
  scope: storageResourceGroup
  name: 'storage-role-contributor-aca-backend'
  params: {
    principalId: acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Used to issue search queries
// https://learn.microsoft.com/azure/search/search-security-rbac
module searchRoleBackend 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

module speechRoleBackend 'core/security/role.bicep' = {
  scope: speechResourceGroup
  name: 'speech-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: 'f2dc8367-1007-4938-bd23-fe263f013447'
    principalType: 'ServicePrincipal'
  }
}

// RBAC for Cosmos DB
// https://learn.microsoft.com/azure/cosmos-db/nosql/security/how-to-grant-data-plane-role-based-access
module cosmosDbRoleBackend 'core/security/documentdb-sql-role.bicep' = if (useAuthentication && useChatHistoryCosmos) {
  scope: cosmosDbResourceGroup
  name: 'cosmosdb-role-backend'
  params: {
    databaseAccountName: (useAuthentication && useChatHistoryCosmos) ? cosmosDb!.outputs.name : ''
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    // Cosmos DB Built-in Data Contributor role
    roleDefinitionId: (useAuthentication && useChatHistoryCosmos)
      ? '/${subscription().id}/resourceGroups/${cosmosDb!.outputs.resourceGroupName}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmosDb!.outputs.name}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
      : ''
  }
}

module isolation 'network-isolation.bicep' = if (usePrivateEndpoint) {
  name: 'networks'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    vnetName: '${abbrs.virtualNetworks}${resourceToken}'
    deploymentTarget: deploymentTarget
    useVpnGateway: useVpnGateway
    vpnGatewayName: useVpnGateway ? '${abbrs.networkVpnGateways}${resourceToken}' : ''
    dnsResolverName: useVpnGateway ? '${abbrs.privateDnsResolver}${resourceToken}' : ''
  }
}

var environmentData = environment()

var openAiPrivateEndpointConnection = (usePrivateEndpoint && isAzureOpenAiHost && deployAzureOpenAi)
  ? [
      {
        groupId: 'account'
        dnsZoneName: 'privatelink.openai.azure.com'
        resourceIds: [openAi!.outputs.resourceId]
      }
    ]
  : []

var cognitiveServicesPrivateEndpointConnection = (usePrivateEndpoint && (!useLocalPdfParser || useMultimodal || useMediaDescriberAzureCU))
  ? [
      {
        groupId: 'account'
        dnsZoneName: 'privatelink.cognitiveservices.azure.com'
        // Only include generic Cognitive Services-based resources (Form Recognizer / Vision / Content Understanding)
        // Azure OpenAI uses its own privatelink.openai.azure.com zone and already has a separate private endpoint above.
        resourceIds: concat(
          !useLocalPdfParser ? [documentIntelligence.outputs.resourceId] : [],
          useMultimodal ? [vision!.outputs.resourceId] : [],
          useMediaDescriberAzureCU ? [contentUnderstanding!.outputs.resourceId] : []
        )
      }
    ]
  : []

var containerAppsPrivateEndpointConnection = (usePrivateEndpoint && deploymentTarget == 'containerapps')
  ? [
      {
        groupId: 'managedEnvironments'
        dnsZoneName: 'privatelink.${location}.azurecontainerapps.io'
        resourceIds: [containerApps!.outputs.environmentId]
      }
    ]
  : []

var appServicePrivateEndpointConnection = (usePrivateEndpoint && deploymentTarget == 'appservice')
  ? [
      {
        groupId: 'sites'
        dnsZoneName: 'privatelink.azurewebsites.net'
        resourceIds: [backend!.outputs.id]
      }
    ]
  : []
var otherPrivateEndpointConnections = (usePrivateEndpoint)
  ? [
      {
        groupId: 'blob'
        dnsZoneName: 'privatelink.blob.${environmentData.suffixes.storage}'
        resourceIds: concat([storage.outputs.id], useUserUpload ? [userStorage!.outputs.id] : [])
      }
      {
        groupId: 'searchService'
        dnsZoneName: 'privatelink.search.windows.net'
        resourceIds: [searchService.outputs.id]
      }
      {
        groupId: 'sql'
        dnsZoneName: 'privatelink.documents.azure.com'
        resourceIds: (useAuthentication && useChatHistoryCosmos) ? [cosmosDb!.outputs.resourceId] : []
      }
    ]
  : []

var privateEndpointConnections = concat(otherPrivateEndpointConnections, openAiPrivateEndpointConnection, cognitiveServicesPrivateEndpointConnection, containerAppsPrivateEndpointConnection, appServicePrivateEndpointConnection)

module privateEndpoints 'private-endpoints.bicep' = if (usePrivateEndpoint) {
  name: 'privateEndpoints'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    resourceToken: resourceToken
    privateEndpointConnections: privateEndpointConnections
    applicationInsightsId: useApplicationInsights ? monitoring!.outputs.applicationInsightsId : ''
    logAnalyticsWorkspaceId: useApplicationInsights ? monitoring!.outputs.logAnalyticsWorkspaceId : ''
    vnetName: isolation!.outputs.vnetName
    vnetPeSubnetId: isolation!.outputs.backendSubnetId
  }
}

// Used to read index definitions (required when using authentication)
// https://learn.microsoft.com/azure/search/search-security-rbac
module searchReaderRoleBackend 'core/security/role.bicep' = if (useAuthentication) {
  scope: searchServiceResourceGroup
  name: 'search-reader-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
    principalType: 'ServicePrincipal'
  }
}

// Used to add/remove documents from index (required for user upload feature)
module searchContribRoleBackend 'core/security/role.bicep' = if (useUserUpload) {
  scope: searchServiceResourceGroup
  name: 'search-contrib-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: 'ServicePrincipal'
  }
}

// For Azure AI Vision access by the backend
module visionRoleBackend 'core/security/role.bicep' = if (useMultimodal) {
  scope: visionResourceGroup
  name: 'vision-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

// For document intelligence access by the backend
module documentIntelligenceRoleBackend 'core/security/role.bicep' = if (useUserUpload) {
  scope: documentIntelligenceResourceGroup
  name: 'documentintelligence-role-backend'
  params: {
    principalId: (deploymentTarget == 'appservice')
      ? backend!.outputs.identityPrincipalId
      : acaBackend!.outputs.identityPrincipalId
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
output AZURE_OPENAI_EMB_DIMENSIONS int = embedding.dimensions
output AZURE_OPENAI_CHATGPT_MODEL string = chatGpt.modelName

// Specific to Azure OpenAI
output AZURE_OPENAI_SERVICE string = isAzureOpenAiHost && deployAzureOpenAi ? openAi!.outputs.name : ''
output AZURE_OPENAI_ENDPOINT string = isAzureOpenAiHost && deployAzureOpenAi ? openAi!.outputs.endpoint : ''
output AZURE_OPENAI_RESOURCE_GROUP string = isAzureOpenAiHost ? openAiResourceGroup.name : ''
output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = isAzureOpenAiHost ? chatGpt.deploymentName : ''
output AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION string = isAzureOpenAiHost ? chatGpt.deploymentVersion : ''
output AZURE_OPENAI_CHATGPT_DEPLOYMENT_SKU string = isAzureOpenAiHost ? chatGpt.deploymentSkuName : ''
output AZURE_OPENAI_EMB_DEPLOYMENT string = isAzureOpenAiHost ? embedding.deploymentName : ''
output AZURE_OPENAI_EMB_DEPLOYMENT_VERSION string = isAzureOpenAiHost ? embedding.deploymentVersion : ''
output AZURE_OPENAI_EMB_DEPLOYMENT_SKU string = isAzureOpenAiHost ? embedding.deploymentSkuName : ''
output AZURE_OPENAI_EVAL_DEPLOYMENT string = isAzureOpenAiHost && useEval ? eval.deploymentName : ''
output AZURE_OPENAI_EVAL_DEPLOYMENT_VERSION string = isAzureOpenAiHost && useEval ? eval.deploymentVersion : ''
output AZURE_OPENAI_EVAL_DEPLOYMENT_SKU string = isAzureOpenAiHost && useEval ? eval.deploymentSkuName : ''
output AZURE_OPENAI_EVAL_MODEL string = isAzureOpenAiHost && useEval ? eval.modelName : ''
output AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT string = isAzureOpenAiHost && useAgenticKnowledgeBase ? knowledgeBase.deploymentName : ''
output AZURE_OPENAI_KNOWLEDGEBASE_MODEL string = isAzureOpenAiHost && useAgenticKnowledgeBase ? knowledgeBase.modelName : ''
output AZURE_OPENAI_REASONING_EFFORT string  = defaultReasoningEffort
output AZURE_SEARCH_KNOWLEDGEBASE_RETRIEVAL_REASONING_EFFORT string = defaultRetrievalReasoningEffort
output AZURE_SPEECH_SERVICE_ID string = useSpeechOutputAzure ? speech!.outputs.resourceId : ''
output AZURE_SPEECH_SERVICE_LOCATION string = useSpeechOutputAzure ? speech!.outputs.location : ''

output AZURE_VISION_ENDPOINT string = useMultimodal ? vision!.outputs.endpoint : ''
output AZURE_CONTENTUNDERSTANDING_ENDPOINT string = useMediaDescriberAzureCU ? contentUnderstanding!.outputs.endpoint : ''

output AZURE_DOCUMENTINTELLIGENCE_SERVICE string = documentIntelligence.outputs.name
output AZURE_DOCUMENTINTELLIGENCE_RESOURCE_GROUP string = documentIntelligenceResourceGroup.name

output AZURE_SEARCH_INDEX string = searchIndexName
output AZURE_SEARCH_KNOWLEDGEBASE_NAME string = knowledgeBaseName
output AZURE_SEARCH_SERVICE string = searchService.outputs.name
output AZURE_SEARCH_SERVICE_RESOURCE_GROUP string = searchServiceResourceGroup.name
output AZURE_SEARCH_SEMANTIC_RANKER string = actualSearchServiceSemanticRankerLevel
output AZURE_SEARCH_FIELD_NAME_EMBEDDING string = searchFieldNameEmbedding
output AZURE_SEARCH_USER_ASSIGNED_IDENTITY_RESOURCE_ID string = searchService.outputs.userAssignedIdentityResourceId

output AZURE_COSMOSDB_ACCOUNT string = (useAuthentication && useChatHistoryCosmos) ? cosmosDb!.outputs.name : ''
output AZURE_CHAT_HISTORY_DATABASE string = chatHistoryDatabaseName
output AZURE_CHAT_HISTORY_CONTAINER string = chatHistoryContainerName
output AZURE_CHAT_HISTORY_VERSION string = chatHistoryVersion

output AZURE_STORAGE_ACCOUNT string = storage.outputs.name
output AZURE_STORAGE_CONTAINER string = storageContainerName
output AZURE_STORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output AZURE_USERSTORAGE_ACCOUNT string = useUserUpload ? userStorage!.outputs.name : ''
output AZURE_USERSTORAGE_CONTAINER string = userStorageContainerName
output AZURE_USERSTORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output AZURE_IMAGESTORAGE_CONTAINER string = useMultimodal ? imageStorageContainerName : ''

// Cloud ingestion function skill endpoints & resource IDs
output DOCUMENT_EXTRACTOR_SKILL_ENDPOINT string = useCloudIngestion ? 'https://${functions!.outputs.documentExtractorUrl}/api/extract' : ''
output FIGURE_PROCESSOR_SKILL_ENDPOINT string = useCloudIngestion ? 'https://${functions!.outputs.figureProcessorUrl}/api/process' : ''
output TEXT_PROCESSOR_SKILL_ENDPOINT string = useCloudIngestion ? 'https://${functions!.outputs.textProcessorUrl}/api/process' : ''
// Identifier URI used as authResourceId for all custom skill endpoints
output DOCUMENT_EXTRACTOR_SKILL_AUTH_RESOURCE_ID string = useCloudIngestion ? functions!.outputs.documentExtractorAuthIdentifierUri : ''
output FIGURE_PROCESSOR_SKILL_AUTH_RESOURCE_ID string = useCloudIngestion ? functions!.outputs.figureProcessorAuthIdentifierUri : ''
output TEXT_PROCESSOR_SKILL_AUTH_RESOURCE_ID string = useCloudIngestion ? functions!.outputs.textProcessorAuthIdentifierUri : ''

output AZURE_AI_PROJECT string = useAiProject ? ai!.outputs.projectName : ''

output AZURE_USE_AUTHENTICATION bool = useAuthentication

output BACKEND_URI string = deploymentTarget == 'appservice' ? backend!.outputs.uri : acaBackend!.outputs.uri
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = deploymentTarget == 'containerapps'
  ? containerApps!.outputs.registryLoginServer
  : ''

output AZURE_VPN_CONFIG_DOWNLOAD_LINK string = useVpnGateway ? 'https://portal.azure.com/#@${tenant().tenantId}/resource${isolation!.outputs.virtualNetworkGatewayId}/pointtositeconfiguration' : ''
