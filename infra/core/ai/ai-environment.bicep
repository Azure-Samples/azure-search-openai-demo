@minLength(1)
@description('Primary location for all resources')
param location string

@description('The AI Hub resource name.')
param hubName string
@description('The AI Project resource name.')
param projectName string
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
  }
}


output projectName string = project.outputs.name
