metadata description = 'Creates a Shared Private Link between Azure Cognitive Search Service and another Azure resource.'

@description('The name of the shared private link.')
param name string

@description('The name of an existing Azure Cognitive Search Service.')
param searchName string

@description('The resource ID of the Azure resource to connect to.')
param resourceId string

// See https://learn.microsoft.com/azure/search/search-indexer-howto-access-private?tabs=portal-create#supported-resource-types
@description('Type of the Azure resource to connect to.')
param groupId string

resource search 'Microsoft.Search/searchServices@2021-04-01-preview' existing = {
  name: searchName
}

resource sharedPrivateLinkResources 'Microsoft.Search/searchServices/sharedPrivateLinkResources@2021-04-01-preview' = {
  name: name
  parent: search
  properties: {
    groupId: groupId
    status: 'Approved'
    provisioningState: 'Succeeded'
    requestMessage: 'automatically created by the system'
    privateLinkResourceId: resourceId
  }
}

output name string = sharedPrivateLinkResources.name
output id string = sharedPrivateLinkResources.id
