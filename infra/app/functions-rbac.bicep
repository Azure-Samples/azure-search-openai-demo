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

// Role Definition IDs
var storageBlobDataReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // Read content container
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Write images container
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88' // For AzureWebJobsStorage
var storageTableDataContributorRoleId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3' // For AzureWebJobsStorage
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // OpenAI access
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908' // Document Intelligence, Vision, CU
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Write to search index
var monitoringMetricsPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb' // Application Insights

// Storage: Blob Data Reader (read content container)
module storageBlobReaderRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'storage-blob-reader-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: storageBlobDataReaderRoleId
    principalType: 'ServicePrincipal'
  }
}

// Storage: Blob Data Contributor (write images container, deployment container)
module storageBlobContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'storage-blob-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: storageBlobDataContributorRoleId
    principalType: 'ServicePrincipal'
  }
}

// Storage: Queue Data Contributor (for AzureWebJobsStorage)
module storageQueueContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'storage-queue-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: storageQueueDataContributorRoleId
    principalType: 'ServicePrincipal'
  }
}

// Storage: Table Data Contributor (for AzureWebJobsStorage)
module storageTableContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(storageResourceGroupName)
  name: 'storage-table-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: storageTableDataContributorRoleId
    principalType: 'ServicePrincipal'
  }
}

// Search: Index Data Contributor (write chunks to index)
module searchIndexContributorRole '../core/security/role.bicep' = {
  scope: resourceGroup(searchServiceResourceGroupName)
  name: 'search-index-contributor-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: searchIndexDataContributorRoleId
    principalType: 'ServicePrincipal'
  }
}

// OpenAI: Cognitive Services OpenAI User
module openAiUserRole '../core/security/role.bicep' = {
  scope: resourceGroup(openAiResourceGroupName)
  name: 'openai-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
    principalType: 'ServicePrincipal'
  }
}

// Document Intelligence: Cognitive Services User
module documentIntelligenceUserRole '../core/security/role.bicep' = {
  scope: resourceGroup(documentIntelligenceResourceGroupName)
  name: 'doc-intelligence-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: cognitiveServicesUserRoleId
    principalType: 'ServicePrincipal'
  }
}

// Vision: Cognitive Services User (if multimodal)
module visionUserRole '../core/security/role.bicep' = if (useMultimodal && !empty(visionServiceName)) {
  scope: resourceGroup(visionResourceGroupName)
  name: 'vision-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: cognitiveServicesUserRoleId
    principalType: 'ServicePrincipal'
  }
}

// Content Understanding: Cognitive Services User (if multimodal)
module contentUnderstandingUserRole '../core/security/role.bicep' = if (useMultimodal && !empty(contentUnderstandingServiceName)) {
  scope: resourceGroup(contentUnderstandingResourceGroupName)
  name: 'content-understanding-user-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: cognitiveServicesUserRoleId
    principalType: 'ServicePrincipal'
  }
}

// Application Insights: Monitoring Metrics Publisher
module appInsightsMetricsPublisherRole '../core/security/role.bicep' = {
  name: 'appinsights-metrics-${uniqueString(principalId)}'
  params: {
    principalId: principalId
    roleDefinitionId: monitoringMetricsPublisherRoleId
    principalType: 'ServicePrincipal'
  }
}
