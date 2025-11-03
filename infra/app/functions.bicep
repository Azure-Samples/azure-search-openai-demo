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

// Create deployment containers in storage account
module deploymentContainers 'br/public:avm/res/storage/storage-account:0.8.3' = {
  name: 'function-deployment-containers'
  scope: resourceGroup(storageResourceGroupName)
  params: {
    name: storageAccountName
    location: location
    blobServices: {
      containers: [
        { name: documentExtractorDeploymentContainer }
        { name: figureProcessorDeploymentContainer }
        { name: textProcessorDeploymentContainer }
      ]
    }
  }
}

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

// App Service Plan (Flex Consumption)
module appServicePlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'functions-plan'
  params: {
    name: '${abbrs.webServerFarms}functions-${resourceToken}'
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true // Required for Linux
    location: location
    tags: tags
  }
}

// Document Extractor Function App
module documentExtractor 'functions-app.bicep' = {
  name: 'document-extractor-func'
  params: {
    name: documentExtractorName
    location: location
    tags: union(tags, { 'azd-service-name': 'document-extractor' })
    applicationInsightsName: applicationInsightsName
    appServicePlanId: appServicePlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storageAccountName
    deploymentStorageContainerName: documentExtractorDeploymentContainer
    identityId: documentExtractorIdentity.outputs.resourceId
    identityClientId: documentExtractorIdentity.outputs.clientId
    appSettings: allAppSettings
    instanceMemoryMB: 4096 // High memory for document processing
    maximumInstanceCount: 100
    functionTimeout: '00:10:00' // 10 minutes for long-running extraction
  }
  dependsOn: [
    deploymentContainers
  ]
}

// Figure Processor Function App
module figureProcessor 'functions-app.bicep' = {
  name: 'figure-processor-func'
  params: {
    name: figureProcessorName
    location: location
    tags: union(tags, { 'azd-service-name': 'figure-processor' })
    applicationInsightsName: applicationInsightsName
    appServicePlanId: appServicePlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storageAccountName
    deploymentStorageContainerName: figureProcessorDeploymentContainer
    identityId: figureProcessorIdentity.outputs.resourceId
    identityClientId: figureProcessorIdentity.outputs.clientId
    appSettings: allAppSettings
    instanceMemoryMB: 2048
    maximumInstanceCount: 100
    functionTimeout: '00:05:00'
  }
  dependsOn: [
    deploymentContainers
  ]
}

// Text Processor Function App
module textProcessor 'functions-app.bicep' = {
  name: 'text-processor-func'
  params: {
    name: textProcessorName
    location: location
    tags: union(tags, { 'azd-service-name': 'text-processor' })
    applicationInsightsName: applicationInsightsName
    appServicePlanId: appServicePlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storageAccountName
    deploymentStorageContainerName: textProcessorDeploymentContainer
    identityId: textProcessorIdentity.outputs.resourceId
    identityClientId: textProcessorIdentity.outputs.clientId
    appSettings: allAppSettings
    instanceMemoryMB: 2048 // Standard memory for embedding
    maximumInstanceCount: 100
    functionTimeout: '00:05:00' // 5 minutes default
  }
  dependsOn: [
    deploymentContainers
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
output figureProcessorName string = figureProcessor.outputs.name
output figureProcessorUrl string = figureProcessor.outputs.defaultHostname
output figureProcessorIdentityPrincipalId string = figureProcessorIdentity.outputs.principalId
output textProcessorName string = textProcessor.outputs.name
output textProcessorUrl string = textProcessor.outputs.defaultHostname
output textProcessorIdentityPrincipalId string = textProcessorIdentity.outputs.principalId
output appServicePlanId string = appServicePlan.outputs.resourceId
