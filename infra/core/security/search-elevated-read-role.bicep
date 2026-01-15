metadata description = 'Creates a custom role definition for elevated read access on Azure AI Search indexes.'

@description('Name of the Azure AI Search service to scope the role to.')
param searchServiceName string

@description('Friendly name of the custom role.')
param roleName string = 'Search Index Elevated Reader'

@description('Description of the custom role.')
param roleDescription string = 'Allows elevated read access to Azure AI Search indexes for investigating ACL-filtered query results.'

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

resource searchElevatedReadRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, searchService.id, roleName)
  properties: {
    roleName: roleName
    description: roleDescription
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.Search/searchServices/indexes/contentSecurity/elevatedOperations/read'
        ]
        notDataActions: []
      }
    ]
    assignableScopes: [
      resourceGroup().id
    ]
  }
}

output roleDefinitionId string = searchElevatedReadRole.id
output roleDefinitionName string = searchElevatedReadRole.name
