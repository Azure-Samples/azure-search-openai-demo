targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Resource group name')
param resourceGroupName string = ''

// Azure AI Search
param searchServiceName string = ''
@allowed(['basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
param searchServiceSkuName string = 'basic'
param searchIndexName string = 'documents'
param searchFieldNameEmbedding string = 'embedding'

// Azure Storage
param storageAccountName string = ''
param storageContainerName string = 'content'
param imageStorageContainerName string = 'images'
@allowed(['Standard_LRS', 'Standard_GRS', 'Standard_ZRS'])
param storageSkuName string = 'Standard_LRS'

// Azure OpenAI
param openAiServiceName string = ''
param openAiLocation string = ''
param openAiSkuName string = 'S0'
param openAiEmbeddingDeploymentName string = 'text-embedding'
param openAiEmbeddingModelName string = 'text-embedding-ada-002'
param openAiEmbeddingDeploymentCapacity int = 30
param openAiChatDeploymentName string = ''
param openAiChatModelName string = 'gpt-4o'
param openAiChatDeploymentCapacity int = 10

// Document Intelligence (optional)
param documentIntelligenceServiceName string = ''
param documentIntelligenceLocation string = ''
@allowed(['F0', 'S0'])
param documentIntelligenceSkuName string = 'S0'

// Azure Functions for cloud ingestion
param useCloudIngestion bool = true
param functionAppPlanName string = ''
param documentExtractorFunctionName string = ''
param figureProcessorFunctionName string = ''
param textProcessorFunctionName string = ''

// Feature flags
param useMultimodal bool = false
param useVectors bool = true

// Tags
var tags = {
  'azd-env-name': environmentName
  'purpose': 'document-ingestion'
}

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// User Assigned Identity for Functions
module userAssignedIdentity 'core/security/user-assigned-identity.bicep' = {
  name: 'user-assigned-identity'
  scope: rg
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
    location: location
    tags: tags
  }
}

// Storage Account
module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: storageSkuName
    }
    containers: [
      { name: storageContainerName }
      { name: imageStorageContainerName }
    ]
  }
}

// Azure AI Search
module search 'core/search/search-services.bicep' = {
  name: 'search'
  scope: rg
  params: {
    name: !empty(searchServiceName) ? searchServiceName : '${abbrs.searchSearchServices}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: searchServiceSkuName
    }
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

// Azure OpenAI
module openAi 'core/ai/cognitiveservices.bicep' = {
  name: 'openai'
  scope: rg
  params: {
    name: !empty(openAiServiceName) ? openAiServiceName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    location: !empty(openAiLocation) ? openAiLocation : location
    tags: tags
    sku: {
      name: openAiSkuName
    }
    deployments: concat(
      [
        {
          name: openAiEmbeddingDeploymentName
          model: {
            format: 'OpenAI'
            name: openAiEmbeddingModelName
            version: '2'
          }
          sku: {
            name: 'Standard'
            capacity: openAiEmbeddingDeploymentCapacity
          }
        }
      ],
      !empty(openAiChatDeploymentName) ? [
        {
          name: openAiChatDeploymentName
          model: {
            format: 'OpenAI'
            name: openAiChatModelName
            version: '2024-08-06'
          }
          sku: {
            name: 'Standard'
            capacity: openAiChatDeploymentCapacity
          }
        }
      ] : []
    )
  }
}

// Document Intelligence (optional)
module documentIntelligence 'core/ai/cognitiveservices.bicep' = if (!empty(documentIntelligenceServiceName) || !empty(documentIntelligenceLocation)) {
  name: 'document-intelligence'
  scope: rg
  params: {
    name: !empty(documentIntelligenceServiceName) ? documentIntelligenceServiceName : '${abbrs.cognitiveServicesAccounts}di-${resourceToken}'
    location: !empty(documentIntelligenceLocation) ? documentIntelligenceLocation : location
    tags: tags
    kind: 'FormRecognizer'
    sku: {
      name: documentIntelligenceSkuName
    }
  }
}

// Function App Plan (for cloud ingestion)
module functionAppPlan 'core/host/functions-plan.bicep' = if (useCloudIngestion) {
  name: 'function-app-plan'
  scope: rg
  params: {
    name: !empty(functionAppPlanName) ? functionAppPlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'Y1'
      tier: 'Dynamic'
    }
  }
}

// Document Extractor Function
module documentExtractorFunction 'core/host/functions.bicep' = if (useCloudIngestion) {
  name: 'document-extractor-function'
  scope: rg
  params: {
    name: !empty(documentExtractorFunctionName) ? documentExtractorFunctionName : '${abbrs.webSitesFunctions}extract-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'document-extractor' })
    appServicePlanId: functionAppPlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storage.outputs.name
    identityType: 'UserAssigned'
    identityId: userAssignedIdentity.outputs.id
    appSettings: [
      { name: 'AZURE_CLIENT_ID', value: userAssignedIdentity.outputs.clientId }
      { name: 'AZURE_STORAGE_ACCOUNT', value: storage.outputs.name }
      { name: 'AZURE_STORAGE_CONTAINER', value: storageContainerName }
      { name: 'AZURE_STORAGE_RESOURCE_GROUP', value: rg.name }
      { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
      { name: 'AZURE_DOCUMENTINTELLIGENCE_SERVICE', value: !empty(documentIntelligenceServiceName) || !empty(documentIntelligenceLocation) ? documentIntelligence.outputs.name : '' }
      { name: 'USE_MULTIMODAL', value: string(useMultimodal) }
      { name: 'USE_LOCAL_PDF_PARSER', value: 'false' }
      { name: 'USE_LOCAL_HTML_PARSER', value: 'true' }
    ]
  }
}

// Figure Processor Function
module figureProcessorFunction 'core/host/functions.bicep' = if (useCloudIngestion) {
  name: 'figure-processor-function'
  scope: rg
  params: {
    name: !empty(figureProcessorFunctionName) ? figureProcessorFunctionName : '${abbrs.webSitesFunctions}figure-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'figure-processor' })
    appServicePlanId: functionAppPlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storage.outputs.name
    identityType: 'UserAssigned'
    identityId: userAssignedIdentity.outputs.id
    appSettings: [
      { name: 'AZURE_CLIENT_ID', value: userAssignedIdentity.outputs.clientId }
      { name: 'AZURE_STORAGE_ACCOUNT', value: storage.outputs.name }
      { name: 'AZURE_IMAGESTORAGE_CONTAINER', value: imageStorageContainerName }
      { name: 'AZURE_OPENAI_SERVICE', value: openAi.outputs.name }
      { name: 'AZURE_OPENAI_CHATGPT_DEPLOYMENT', value: openAiChatDeploymentName }
      { name: 'AZURE_OPENAI_CHATGPT_MODEL', value: openAiChatModelName }
      { name: 'USE_MULTIMODAL', value: string(useMultimodal) }
    ]
  }
}

// Text Processor Function
module textProcessorFunction 'core/host/functions.bicep' = if (useCloudIngestion) {
  name: 'text-processor-function'
  scope: rg
  params: {
    name: !empty(textProcessorFunctionName) ? textProcessorFunctionName : '${abbrs.webSitesFunctions}text-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'text-processor' })
    appServicePlanId: functionAppPlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storage.outputs.name
    identityType: 'UserAssigned'
    identityId: userAssignedIdentity.outputs.id
    appSettings: [
      { name: 'AZURE_CLIENT_ID', value: userAssignedIdentity.outputs.clientId }
      { name: 'AZURE_OPENAI_SERVICE', value: openAi.outputs.name }
      { name: 'AZURE_OPENAI_EMB_DEPLOYMENT', value: openAiEmbeddingDeploymentName }
      { name: 'AZURE_OPENAI_EMB_MODEL_NAME', value: openAiEmbeddingModelName }
      { name: 'AZURE_DOCUMENTINTELLIGENCE_SERVICE', value: !empty(documentIntelligenceServiceName) || !empty(documentIntelligenceLocation) ? documentIntelligence.outputs.name : '' }
      { name: 'USE_VECTORS', value: string(useVectors) }
      { name: 'USE_MULTIMODAL', value: string(useMultimodal) }
      { name: 'OPENAI_HOST', value: 'azure' }
    ]
  }
}

// Role Assignments
module storageRoleUser 'core/security/role.bicep' = {
  name: 'storage-role-user'
  scope: rg
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module searchRoleUser 'core/security/role.bicep' = {
  name: 'search-role-user'
  scope: rg
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module openAiRoleUser 'core/security/role.bicep' = {
  name: 'openai-role-user'
  scope: rg
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_RESOURCE_GROUP string = rg.name

output AZURE_STORAGE_ACCOUNT string = storage.outputs.name
output AZURE_STORAGE_CONTAINER string = storageContainerName
output AZURE_IMAGESTORAGE_CONTAINER string = imageStorageContainerName
output AZURE_STORAGE_RESOURCE_GROUP string = rg.name

output AZURE_SEARCH_SERVICE string = search.outputs.name
output AZURE_SEARCH_INDEX string = searchIndexName
output AZURE_SEARCH_FIELD_NAME_EMBEDDING string = searchFieldNameEmbedding

output AZURE_OPENAI_SERVICE string = openAi.outputs.name
output AZURE_OPENAI_EMB_DEPLOYMENT string = openAiEmbeddingDeploymentName
output AZURE_OPENAI_EMB_MODEL_NAME string = openAiEmbeddingModelName
output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = openAiChatDeploymentName
output AZURE_OPENAI_CHATGPT_MODEL string = openAiChatModelName

output AZURE_DOCUMENTINTELLIGENCE_SERVICE string = !empty(documentIntelligenceServiceName) || !empty(documentIntelligenceLocation) ? documentIntelligence.outputs.name : ''

output USE_VECTORS string = string(useVectors)
output USE_MULTIMODAL string = string(useMultimodal)
output USE_CLOUD_INGESTION string = string(useCloudIngestion)

output AZURE_FUNCTION_DOCUMENT_EXTRACTOR_URI string = useCloudIngestion ? 'https://${documentExtractorFunction.outputs.uri}/api/extract' : ''
output AZURE_FUNCTION_FIGURE_PROCESSOR_URI string = useCloudIngestion ? 'https://${figureProcessorFunction.outputs.uri}/api/process' : ''
output AZURE_FUNCTION_TEXT_PROCESSOR_URI string = useCloudIngestion ? 'https://${textProcessorFunction.outputs.uri}/api/process' : ''
output AZURE_USER_ASSIGNED_IDENTITY_ID string = userAssignedIdentity.outputs.id
