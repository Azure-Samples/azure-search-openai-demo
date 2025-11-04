// Parameters for both function apps
param location string = resourceGroup().location
param tags object = {}
param applicationInsightsName string
param storageAccountName string
param storageResourceGroupName string
param searchServiceName string
param searchServiceResourceGroupName string
param openAiServiceName string
param openAiResourceGroupName string
param documentIntelligenceServiceName string
param documentIntelligenceResourceGroupName string
param visionServiceName string = ''
param visionResourceGroupName string = ''
param contentUnderstandingServiceName string = ''
param contentUnderstandingResourceGroupName string = ''

// Function App Names
param documentExtractorName string
param figureProcessorName string
param textProcessorName string
// OpenID issuer provided by main template (e.g. https://login.microsoftonline.com/<tenantId>/v2.0)
param openIdIssuer string

// Shared configuration
param useVectors bool
param useMultimodal bool
param useLocalPdfParser bool
param useLocalHtmlParser bool
param useMediaDescriberAzureCU bool
param searchIndexName string
param searchFieldNameEmbedding string
param openAiEmbDeployment string
param openAiEmbModelName string
param openAiEmbDimensions int
param openAiApiVersion string
param openAiChatDeployment string
param openAiChatModelName string
param openAiCustomUrl string

var abbrs = loadJsonContent('../abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, resourceGroup().id, location))

var documentExtractorRuntimeStorageName = '${abbrs.storageStorageAccounts}doc${take(resourceToken, 18)}'
var figureProcessorRuntimeStorageName = '${abbrs.storageStorageAccounts}fig${take(resourceToken, 18)}'
var textProcessorRuntimeStorageName = '${abbrs.storageStorageAccounts}txt${take(resourceToken, 18)}'

var documentExtractorHostId = 'doc-skill-${take(resourceToken, 12)}'
var figureProcessorHostId = 'fig-skill-${take(resourceToken, 12)}'
var textProcessorHostId = 'txt-skill-${take(resourceToken, 12)}'

var runtimeStorageRoles = [
  {
    suffix: 'blob'
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  }
  {
    suffix: 'queue'
    roleDefinitionId: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  }
  {
    suffix: 'table'
    roleDefinitionId: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
  }
]

// Common app settings for both functions
var commonAppSettings = {
  // Storage
  AZURE_STORAGE_ACCOUNT: storageAccountName
  AZURE_STORAGE_CONTAINER: 'content'
  AZURE_IMAGESTORAGE_CONTAINER: 'images'

  // Azure OpenAI
  AZURE_OPENAI_SERVICE: openAiServiceName
  AZURE_OPENAI_EMB_DEPLOYMENT: openAiEmbDeployment
  AZURE_OPENAI_EMB_MODEL_NAME: openAiEmbModelName
  AZURE_OPENAI_EMB_DIMENSIONS: string(openAiEmbDimensions)
  AZURE_OPENAI_API_VERSION: openAiApiVersion
  AZURE_OPENAI_CHATGPT_DEPLOYMENT: openAiChatDeployment
  AZURE_OPENAI_CHATGPT_MODEL: openAiChatModelName
  AZURE_OPENAI_CUSTOM_URL: openAiCustomUrl

  // Azure AI Search
  AZURE_SEARCH_SERVICE: searchServiceName
  AZURE_SEARCH_INDEX: searchIndexName
  AZURE_SEARCH_FIELD_NAME_EMBEDDING: searchFieldNameEmbedding

  // Document Intelligence
  AZURE_DOCUMENTINTELLIGENCE_SERVICE: documentIntelligenceServiceName

  // Feature flags
  USE_VECTORS: string(useVectors)
  USE_MULTIMODAL: string(useMultimodal)
  USE_LOCAL_PDF_PARSER: string(useLocalPdfParser)
  USE_LOCAL_HTML_PARSER: string(useLocalHtmlParser)
  USE_MEDIA_DESCRIBER_AZURE_CU: string(useMediaDescriberAzureCU)
}

// Add optional vision settings
var visionSettings = useMultimodal && !empty(visionServiceName) ? {
  AZURE_VISION_ENDPOINT: 'https://${visionServiceName}.cognitiveservices.azure.com/'
} : {}

// Add optional content understanding settings
var contentUnderstandingSettings = useMultimodal && !empty(contentUnderstandingServiceName) ? {
  AZURE_CONTENTUNDERSTANDING_ENDPOINT: 'https://${contentUnderstandingServiceName}.cognitiveservices.azure.com/'
} : {}

// Merge all settings
var allAppSettings = union(commonAppSettings, visionSettings, contentUnderstandingSettings)

// Deployment storage containers
var documentExtractorDeploymentContainer = 'deploy-doc-extractor-${take(resourceToken, 7)}'
var figureProcessorDeploymentContainer = 'deploy-figure-processor-${take(resourceToken, 7)}'
var textProcessorDeploymentContainer = 'deploy-text-processor-${take(resourceToken, 7)}'

// Runtime storage accounts per function (Flex Consumption requirement)
module documentExtractorRuntimeStorageAccount '../core/storage/storage-account.bicep' = {
  name: 'doc-extractor-runtime-storage'
  params: {
    name: documentExtractorRuntimeStorageName
    location: location
    tags: tags
    allowBlobPublicAccess: false
    containers: [
      {
        name: documentExtractorDeploymentContainer
      }
    ]
  }
}

module figureProcessorRuntimeStorageAccount '../core/storage/storage-account.bicep' = {
  name: 'figure-processor-runtime-storage'
  params: {
    name: figureProcessorRuntimeStorageName
    location: location
    tags: tags
    allowBlobPublicAccess: false
    containers: [
      {
        name: figureProcessorDeploymentContainer
      }
    ]
  }
}

module textProcessorRuntimeStorageAccount '../core/storage/storage-account.bicep' = {
  name: 'text-processor-runtime-storage'
  params: {
    name: textProcessorRuntimeStorageName
    location: location
    tags: tags
    allowBlobPublicAccess: false
    containers: [
      {
        name: textProcessorDeploymentContainer
      }
    ]
  }
}

resource documentExtractorRuntimeStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: documentExtractorRuntimeStorageName
}

resource figureProcessorRuntimeStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: figureProcessorRuntimeStorageName
}

resource textProcessorRuntimeStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: textProcessorRuntimeStorageName
}

resource documentExtractorRuntimeStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for role in runtimeStorageRoles: {
  name: guid(documentExtractorRuntimeStorage.id, role.roleDefinitionId, 'doc-runtime')
  scope: documentExtractorRuntimeStorage
  properties: {
    principalId: documentExtractorIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', role.roleDefinitionId)
  }
  dependsOn: [
    documentExtractorRuntimeStorageAccount
  ]
}]

resource figureProcessorRuntimeStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for role in runtimeStorageRoles: {
  name: guid(figureProcessorRuntimeStorage.id, role.roleDefinitionId, 'figure-runtime')
  scope: figureProcessorRuntimeStorage
  properties: {
    principalId: figureProcessorIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', role.roleDefinitionId)
  }
  dependsOn: [
    figureProcessorRuntimeStorageAccount
  ]
}]

resource textProcessorRuntimeStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for role in runtimeStorageRoles: {
  name: guid(textProcessorRuntimeStorage.id, role.roleDefinitionId, 'text-runtime')
  scope: textProcessorRuntimeStorage
  properties: {
    principalId: textProcessorIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', role.roleDefinitionId)
  }
  dependsOn: [
    textProcessorRuntimeStorageAccount
  ]
}]

// User-assigned managed identity for document extractor
module documentExtractorIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'doc-extractor-identity'
  params: {
    location: location
    tags: tags
    name: '${abbrs.managedIdentityUserAssignedIdentities}doc-extractor-${resourceToken}'
  }
}

// User-assigned managed identity for text processor
module textProcessorIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'text-processor-identity'
  params: {
    location: location
    tags: tags
    name: '${abbrs.managedIdentityUserAssignedIdentities}text-processor-${resourceToken}'
  }
}

// User-assigned managed identity for figure processor
module figureProcessorIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'figure-processor-identity'
  params: {
    location: location
    tags: tags
    name: '${abbrs.managedIdentityUserAssignedIdentities}figure-processor-${resourceToken}'
  }
}

// Flex Consumption supports only one Function App per plan; create a dedicated plan per ingestion function
module documentExtractorPlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'doc-extractor-plan'
  params: {
    name: '${abbrs.webServerFarms}doc-extractor-${resourceToken}'
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true
    location: location
    tags: tags
  }
}

module figureProcessorPlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'figure-processor-plan'
  params: {
    name: '${abbrs.webServerFarms}figure-processor-${resourceToken}'
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true
    location: location
    tags: tags
  }
}

module textProcessorPlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'text-processor-plan'
  params: {
    name: '${abbrs.webServerFarms}text-processor-${resourceToken}'
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true
    location: location
    tags: tags
  }
}

// Document Extractor Function App
// App registration for document extractor (uses function identity principalId as FIC subject)
module documentExtractorAppReg '../core/auth/appregistration.bicep' = {
  name: 'doc-extractor-appreg'
  params: {
    cloudEnvironment: environment().name
    webAppIdentityId: documentExtractorIdentity.outputs.principalId
    clientAppName: 'skill-${documentExtractorName}'
    clientAppDisplayName: 'skill-${documentExtractorName}'
    issuer: openIdIssuer
    webAppEndpoint: 'https://${documentExtractorName}.azurewebsites.net'
  }
}

module documentExtractor 'functions-app.bicep' = {
  name: 'document-extractor-func'
  params: {
    name: documentExtractorName
    location: location
    tags: union(tags, { 'azd-service-name': 'document-extractor' })
    applicationInsightsName: applicationInsightsName
    appServicePlanId: documentExtractorPlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: documentExtractorRuntimeStorageName
    deploymentStorageContainerName: documentExtractorDeploymentContainer
    identityId: documentExtractorIdentity.outputs.resourceId
    identityClientId: documentExtractorIdentity.outputs.clientId
    appSettings: union(allAppSettings, {
      AzureFunctionsWebHost__hostid: documentExtractorHostId
    })
    instanceMemoryMB: 4096 // High memory for document processing
    maximumInstanceCount: 100
    // Removed unused functionTimeout parameter; configured defaults via host settings
    skillAppClientId: documentExtractorAppReg.outputs.clientAppId
    skillAppAudience: 'api://${documentExtractorAppReg.outputs.clientAppId}'
  }
  dependsOn: [
    documentExtractorRuntimeStorageAccount
  ]
}

// Figure Processor Function App
module figureProcessorAppReg '../core/auth/appregistration.bicep' = {
  name: 'figure-processor-appreg'
  params: {
    cloudEnvironment: environment().name
    webAppIdentityId: figureProcessorIdentity.outputs.principalId
    clientAppName: 'skill-${figureProcessorName}'
    clientAppDisplayName: 'skill-${figureProcessorName}'
    issuer: openIdIssuer
    webAppEndpoint: 'https://${figureProcessorName}.azurewebsites.net'
  }
}

module figureProcessor 'functions-app.bicep' = {
  name: 'figure-processor-func'
  params: {
    name: figureProcessorName
    location: location
    tags: union(tags, { 'azd-service-name': 'figure-processor' })
    applicationInsightsName: applicationInsightsName
    appServicePlanId: figureProcessorPlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: figureProcessorRuntimeStorageName
    deploymentStorageContainerName: figureProcessorDeploymentContainer
    identityId: figureProcessorIdentity.outputs.resourceId
    identityClientId: figureProcessorIdentity.outputs.clientId
    appSettings: union(allAppSettings, {
      AzureFunctionsWebHost__hostid: figureProcessorHostId
    })
    instanceMemoryMB: 2048
    maximumInstanceCount: 100
    skillAppClientId: figureProcessorAppReg.outputs.clientAppId
    skillAppAudience: 'api://${figureProcessorAppReg.outputs.clientAppId}'
  }
  dependsOn: [
    figureProcessorRuntimeStorageAccount
  ]
}

// Text Processor Function App
module textProcessorAppReg '../core/auth/appregistration.bicep' = {
  name: 'text-processor-appreg'
  params: {
    cloudEnvironment: environment().name
    webAppIdentityId: textProcessorIdentity.outputs.principalId
    clientAppName: 'skill-${textProcessorName}'
    clientAppDisplayName: 'skill-${textProcessorName}'
    issuer: openIdIssuer
    webAppEndpoint: 'https://${textProcessorName}.azurewebsites.net'
  }
}

module textProcessor 'functions-app.bicep' = {
  name: 'text-processor-func'
  params: {
    name: textProcessorName
    location: location
    tags: union(tags, { 'azd-service-name': 'text-processor' })
    applicationInsightsName: applicationInsightsName
    appServicePlanId: textProcessorPlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: textProcessorRuntimeStorageName
    deploymentStorageContainerName: textProcessorDeploymentContainer
    identityId: textProcessorIdentity.outputs.resourceId
    identityClientId: textProcessorIdentity.outputs.clientId
    appSettings: union(allAppSettings, {
      AzureFunctionsWebHost__hostid: textProcessorHostId
    })
    instanceMemoryMB: 2048 // Standard memory for embedding
    maximumInstanceCount: 100
    skillAppClientId: textProcessorAppReg.outputs.clientAppId
    skillAppAudience: 'api://${textProcessorAppReg.outputs.clientAppId}'
  }
  dependsOn: [
    textProcessorRuntimeStorageAccount
  ]
}

// RBAC: Document Extractor Roles
module documentExtractorRbac 'functions-rbac.bicep' = {
  name: 'doc-extractor-rbac'
  params: {
    principalId: documentExtractorIdentity.outputs.principalId
    storageResourceGroupName: storageResourceGroupName
    searchServiceResourceGroupName: searchServiceResourceGroupName
    openAiResourceGroupName: openAiResourceGroupName
    documentIntelligenceResourceGroupName: documentIntelligenceResourceGroupName
    visionServiceName: visionServiceName
    visionResourceGroupName: visionResourceGroupName
    contentUnderstandingServiceName: contentUnderstandingServiceName
    contentUnderstandingResourceGroupName: contentUnderstandingResourceGroupName
    useMultimodal: useMultimodal
  }
}

// RBAC: Text Processor Roles
module textProcessorRbac 'functions-rbac.bicep' = {
  name: 'text-processor-rbac'
  params: {
    principalId: textProcessorIdentity.outputs.principalId
    storageResourceGroupName: storageResourceGroupName
    searchServiceResourceGroupName: searchServiceResourceGroupName
    openAiResourceGroupName: openAiResourceGroupName
    documentIntelligenceResourceGroupName: documentIntelligenceResourceGroupName
    visionServiceName: visionServiceName
    visionResourceGroupName: visionResourceGroupName
    contentUnderstandingServiceName: contentUnderstandingServiceName
    contentUnderstandingResourceGroupName: contentUnderstandingResourceGroupName
    useMultimodal: useMultimodal
  }
}

// RBAC: Figure Processor Roles
module figureProcessorRbac 'functions-rbac.bicep' = {
  name: 'figure-processor-rbac'
  params: {
    principalId: figureProcessorIdentity.outputs.principalId
    storageResourceGroupName: storageResourceGroupName
    searchServiceResourceGroupName: searchServiceResourceGroupName
    openAiResourceGroupName: openAiResourceGroupName
    documentIntelligenceResourceGroupName: documentIntelligenceResourceGroupName
    visionServiceName: visionServiceName
    visionResourceGroupName: visionResourceGroupName
    contentUnderstandingServiceName: contentUnderstandingServiceName
    contentUnderstandingResourceGroupName: contentUnderstandingResourceGroupName
    useMultimodal: useMultimodal
  }
}

// Outputs
output documentExtractorName string = documentExtractor.outputs.name
output documentExtractorUrl string = documentExtractor.outputs.defaultHostname
output documentExtractorIdentityPrincipalId string = documentExtractorIdentity.outputs.principalId
output documentExtractorClientAppId string = documentExtractorAppReg.outputs.clientAppId
output documentExtractorSkillResourceId string = documentExtractorAppReg.outputs.clientAppId
output figureProcessorName string = figureProcessor.outputs.name
output figureProcessorUrl string = figureProcessor.outputs.defaultHostname
output figureProcessorIdentityPrincipalId string = figureProcessorIdentity.outputs.principalId
output figureProcessorClientAppId string = figureProcessorAppReg.outputs.clientAppId
output figureProcessorSkillResourceId string = figureProcessorAppReg.outputs.clientAppId
output textProcessorName string = textProcessor.outputs.name
output textProcessorUrl string = textProcessor.outputs.defaultHostname
output textProcessorIdentityPrincipalId string = textProcessorIdentity.outputs.principalId
output textProcessorClientAppId string = textProcessorAppReg.outputs.clientAppId
output textProcessorSkillResourceId string = textProcessorAppReg.outputs.clientAppId
output documentExtractorRuntimeStorageName string = documentExtractorRuntimeStorageName
output figureProcessorRuntimeStorageName string = figureProcessorRuntimeStorageName
output textProcessorRuntimeStorageName string = textProcessorRuntimeStorageName
output documentExtractorHostId string = documentExtractorHostId
output figureProcessorHostId string = figureProcessorHostId
output textProcessorHostId string = textProcessorHostId
// Output the last plan id (text processor) for potential diagnostics; others can be added if needed
output appServicePlanId string = textProcessorPlan.outputs.resourceId
// Resource IDs for each function app (used for auth_resource_id with managed identity secured skills)
output documentExtractorResourceId string = documentExtractor.outputs.resourceId
output figureProcessorResourceId string = figureProcessor.outputs.resourceId
output textProcessorResourceId string = textProcessor.outputs.resourceId
