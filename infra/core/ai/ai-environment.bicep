@minLength(1)
@description('Primary location for all resources')
param location string

@description('The AI Hub resource name.')
param hubName string
@description('The AI Project resource name.')
param projectName string
@description('The Key Vault resource name.')
param keyVaultId string
@description('The Key Vault resource name.')
param keyVaultName string
@description('The Storage Account resource ID.')
param storageAccountId string
@description('The Application Insights resource ID.')
param applicationInsightsId string = ''
@description('The Azure Search resource name.')
param searchServiceName string = ''
@description('The Azure Search connection name.')
param searchConnectionName string = ''
param tags object = {}

module hub './hub.bicep' = {
  name: 'hub'
  params: {
    location: location
    tags: tags
    name: hubName
    displayName: hubName
    keyVaultId: keyVaultId
    storageAccountId: storageAccountId
    containerRegistryId: null
    applicationInsightsId: applicationInsightsId
    aiSearchName: searchServiceName
    aiSearchConnectionName: searchConnectionName
  }
}

module project './project.bicep' = {
  name: 'project'
  params: {
    location: location
    tags: tags
    name: projectName
    displayName: projectName
    hubName: hub.outputs.name
    keyVaultName: keyVaultName
  }
}

// Outputs
// Resource Group
output resourceGroupName string = resourceGroup().name

// Hub
output hubName string = hub.outputs.name
output hubPrincipalId string = hub.outputs.principalId

// Project
output projectName string = project.outputs.name
output projectPrincipalId string = project.outputs.principalId

//Discoveryurl
output discoveryUrl string = project.outputs.discoveryUrl
