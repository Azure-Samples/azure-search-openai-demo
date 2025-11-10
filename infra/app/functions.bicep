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
// TODO: Take the settings from main.bicep - appEnvVars
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
// TODO: Can we just use a boring name, the same for all functions?
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
  name: guid(documentExtractorRuntimeStorage.id, role.roleDefinitionId, 'doc-storage-roles')
  scope: documentExtractorRuntimeStorage
  properties: {
    principalId: functionsUserIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', role.roleDefinitionId)
  }
  dependsOn: [
    documentExtractorRuntimeStorageAccount
  ]
}]

resource figureProcessorRuntimeStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for role in runtimeStorageRoles: {
  name: guid(figureProcessorRuntimeStorage.id, role.roleDefinitionId, 'figure-storage-roles')
  scope: figureProcessorRuntimeStorage
  properties: {
    principalId: functionsUserIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', role.roleDefinitionId)
  }
  dependsOn: [
    figureProcessorRuntimeStorageAccount
  ]
}]

resource textProcessorRuntimeStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for role in runtimeStorageRoles: {
  name: guid(textProcessorRuntimeStorage.id, role.roleDefinitionId, 'text-storage-roles')
  scope: textProcessorRuntimeStorage
  properties: {
    principalId: functionsUserIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', role.roleDefinitionId)
  }
  dependsOn: [
    textProcessorRuntimeStorageAccount
  ]
}]

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


module functionsUserIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'functions-user-identity'
  params: {
    location: location
    tags: tags
    name: 'functions-user-identity-${resourceToken}'
  }
}



// Document Extractor Function App
// App registration for document extractor (uses function identity principalId as FIC subject)
module documentExtractorAppReg '../core/auth/appregistration.bicep' = {
  name: 'doc-extractor-appreg'
  params: {
    appUniqueName: '${documentExtractorName}-appreg'
    cloudEnvironment: environment().name
    webAppIdentityId: functionsUserIdentity.outputs.principalId
    clientAppName: '${documentExtractorName}-app'
    clientAppDisplayName: '${documentExtractorName} Entra App'
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
    identityId: functionsUserIdentity.outputs.resourceId
    identityClientId: functionsUserIdentity.outputs.clientId
    authClientId: documentExtractorAppReg.outputs.clientAppId
    authIdentifierUri: documentExtractorAppReg.outputs.identifierUri
    authTenantId: tenant().tenantId
    storageAccountName: documentExtractorRuntimeStorageName
    deploymentStorageContainerName: documentExtractorDeploymentContainer
    appSettings: union(allAppSettings, {
      AzureFunctionsWebHost__hostid: documentExtractorHostId
    })
    instanceMemoryMB: 4096 // High memory for document processing
    maximumInstanceCount: 100
  }
  dependsOn: [
    documentExtractorRuntimeStorageAccount
  ]
}

// Figure Processor Function App
module figureProcessorAppReg '../core/auth/appregistration.bicep' = {
  name: 'figure-processor-appreg'
  params: {
    appUniqueName: '${figureProcessorName}-app'
    cloudEnvironment: environment().name
    webAppIdentityId: functionsUserIdentity.outputs.principalId
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
    identityId: functionsUserIdentity.outputs.resourceId
    identityClientId: functionsUserIdentity.outputs.clientId
    authClientId: figureProcessorAppReg.outputs.clientAppId
    authIdentifierUri: figureProcessorAppReg.outputs.identifierUri
    authTenantId: tenant().tenantId
    appSettings: union(allAppSettings, {
      AzureFunctionsWebHost__hostid: figureProcessorHostId
    })
    instanceMemoryMB: 2048
    maximumInstanceCount: 100
  }
  dependsOn: [
    figureProcessorRuntimeStorageAccount
  ]
}

// Text Processor Function App
module textProcessorAppReg '../core/auth/appregistration.bicep' = {
  name: 'text-processor-appreg'
  params: {
    appUniqueName: '${textProcessorName}-app'
    cloudEnvironment: environment().name
    webAppIdentityId: functionsUserIdentity.outputs.principalId
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
    identityId: functionsUserIdentity.outputs.resourceId
    identityClientId: functionsUserIdentity.outputs.clientId
    authClientId: textProcessorAppReg.outputs.clientAppId
    authIdentifierUri: textProcessorAppReg.outputs.identifierUri
    authTenantId: tenant().tenantId
    appSettings: union(allAppSettings, {
      AzureFunctionsWebHost__hostid: textProcessorHostId
    })
    instanceMemoryMB: 2048 // Standard memory for embedding
    maximumInstanceCount: 100
  }
  dependsOn: [
    textProcessorRuntimeStorageAccount
  ]
}

// RBAC: Document Extractor Roles
module functionsIdentityRBAC 'functions-rbac.bicep' = {
  name: 'doc-extractor-rbac'
  params: {
    principalId: functionsUserIdentity.outputs.principalId
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
output figureProcessorName string = figureProcessor.outputs.name
output figureProcessorUrl string = figureProcessor.outputs.defaultHostname
output textProcessorName string = textProcessor.outputs.name
output textProcessorUrl string = textProcessor.outputs.defaultHostname
// Resource IDs for each function app (used for auth_resource_id with managed identity secured skills)
output documentExtractorAuthIdentifierUri string = documentExtractorAppReg.outputs.identifierUri
output figureProcessorAuthIdentifierUri string = figureProcessorAppReg.outputs.identifierUri
output textProcessorAuthIdentifierUri string = textProcessorAppReg.outputs.identifierUri
