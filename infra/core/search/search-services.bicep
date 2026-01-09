metadata description = 'Creates an Azure AI Search instance.'
param name string
param location string = resourceGroup().location
param tags object = {}

param sku object = {
  name: 'standard'
}

param authOptions object = {}
param disableLocalAuth bool = false
param encryptionWithCmk object = {
  enforcement: 'Unspecified'
}
@allowed([
  'Default'
  'HighDensity'
])
param hostingMode string = 'Default'
@allowed([
  'enabled'
  'disabled'
])
param publicNetworkAccess string = 'enabled'
param partitionCount int = 1
param replicaCount int = 1
@allowed([
  'disabled'
  'free'
  'standard'
])
param semanticSearch string = 'disabled'

param sharedPrivateLinkStorageAccounts array = []

resource searchIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (sku.name != 'free') {
  name: '${name}-identity'
  location: location
  tags: tags
}

var searchIdentityProvider = (sku.name == 'free') ? null : {
  type: 'SystemAssigned, UserAssigned'
  userAssignedIdentities: {
    '${searchIdentity.id}': {}
  }
}

resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: name
  location: location
  tags: tags
  // The free tier does not support managed identity
  identity: searchIdentityProvider
  properties: {
    authOptions: disableLocalAuth ? null : authOptions
    disableLocalAuth: disableLocalAuth
    encryptionWithCmk: encryptionWithCmk
    hostingMode: hostingMode
    partitionCount: partitionCount
    publicNetworkAccess: publicNetworkAccess
    replicaCount: replicaCount
    semanticSearch: semanticSearch
  }
  sku: sku

  resource sharedPrivateLinkResource 'sharedPrivateLinkResources@2025-05-01' = [for (resourceId, i) in sharedPrivateLinkStorageAccounts: {
    name: 'search-shared-private-link-${i}'
    properties: {
      groupId: 'blob'
      status: 'Approved'
      provisioningState: 'Succeeded'
      requestMessage: 'automatically created by the system'
      privateLinkResourceId: resourceId
    }
  }]
}

output id string = search.id
output endpoint string = 'https://${name}.search.windows.net/'
output name string = search.name
output systemAssignedPrincipalId string = (sku.name != 'free') ? search.identity.principalId : ''
output userAssignedPrincipalId string = (sku.name != 'free') ? (searchIdentity.?properties.?principalId ?? '') : ''
output userAssignedIdentityId string = (sku.name != 'free') ? (searchIdentity.?id ?? '') : ''
output userAssignedIdentityClientId string = (sku.name != 'free') ? (searchIdentity.?properties.?clientId ?? '') : ''
output userAssignedIdentityResourceId string = (sku.name != 'free') ? (searchIdentity.?id ?? '') : ''
