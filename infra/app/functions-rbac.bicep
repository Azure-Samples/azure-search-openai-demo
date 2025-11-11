// RBAC assignments for function apps
param principalId string
param storageResourceGroupName string
param searchServiceResourceGroupName string
param openAiResourceGroupName string
param documentIntelligenceResourceGroupName string
param visionServiceName string = ''
param visionResourceGroupName string = ''
param contentUnderstandingServiceName string = ''
param contentUnderstandingResourceGroupName string = ''
param useMultimodal bool


// Storage: Blob Data Reader (read content container)
module storageBlobReaderRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'function-storage-blob-reader-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // Storage Blob Data Reader
    principalType: 'ServicePrincipal'
  }
}

// Storage: Blob Data Contributor (write images container, deployment container)
module storageBlobContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'function-storage-blob-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Storage: Queue Data Contributor (for AzureWebJobsStorage)
module storageQueueContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'function-storage-queue-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: '974c5e8b-45b9-4653-ba55-5f855dd0fb88' // Storage Queue Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Storage: Table Data Contributor (for AzureWebJobsStorage)
module storageTableContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'function-storage-table-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3' // Storage Table Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Search: Index Data Contributor (write chunks to index)
module searchIndexContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(searchServiceResourceGroupName)
  name: 'function-search-index-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// OpenAI: Cognitive Services OpenAI User
module openAiUserRole '../core/security/role.bicep' = {
  scope: resourceGroup(openAiResourceGroupName)
  name: 'function-openai-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    principalType: 'ServicePrincipal'
  }
}

// Document Intelligence: Cognitive Services User
module documentIntelligenceUserRole '../core/security/role.bicep' = {
  scope: resourceGroup(documentIntelligenceResourceGroupName)
  name: 'function-doc-intelligence-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
    principalType: 'ServicePrincipal'
  }
}

// Vision: Cognitive Services User (if multimodal)
module visionUserRole '../core/security/role.bicep' = if (useMultimodal && !empty(visionServiceName)) {
  scope: resourceGroup(visionResourceGroupName)
  name: 'function-vision-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
    principalType: 'ServicePrincipal'
  }
}

// Content Understanding: Cognitive Services User (if multimodal)
module contentUnderstandingUserRole '../core/security/role.bicep' = if (useMultimodal && !empty(contentUnderstandingServiceName)) {
  scope: resourceGroup(contentUnderstandingResourceGroupName)
  name: 'function-content-understanding-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
    principalType: 'ServicePrincipal'
  }
}

// Application Insights: Monitoring Metrics Publisher
module appInsightsMetricsPublisherRole '../core/security/role.bicep' = {
  name: 'function-appinsights-metrics-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: '3913510d-42f4-4e42-8a64-420c390055eb' // Monitoring Metrics Publisher
    principalType: 'ServicePrincipal'
  }
}
