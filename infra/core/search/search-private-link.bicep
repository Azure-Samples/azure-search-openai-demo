param name string
param searchName string
param resourceId string
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
