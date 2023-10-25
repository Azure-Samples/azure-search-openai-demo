param name string
param location string = resourceGroup().location
param tags object = {}

param sku object = {
  name: 'standard'
}

param authOptions object = {}
param semanticSearch string = 'disabled'

param private bool = false
param clientIpAddress string = ''
param vnetName string
param peSubnetName string
//shoud be Disabled for closed environment. Set to Enabled for convenience during the demo/workshop
param publicNetworkAccess string = 'Enabled'

var privateDnsZoneNames = [
  'privatelink.search.windows.net'
]

resource search 'Microsoft.Search/searchServices@2021-04-01-preview' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    authOptions: authOptions
    disableLocalAuth: false
    disabledDataExfiltrationOptions: []
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    hostingMode: 'default'
    publicNetworkAccess: publicNetworkAccess
    networkRuleSet: {
      bypass: 'None'
      // Allow access from the client PC
      ipRules: (private) ? [
        {
          value: clientIpAddress 
        }
      ] : []
    }
    partitionCount: 1
    replicaCount: 1
    semanticSearch: semanticSearch
  }
  sku: sku
}

resource existingVnet 'Microsoft.Network/virtualNetworks@2020-05-01' existing = if ( private ) {
  name: vnetName
  resource existingsubnet 'subnets' existing = {
    name: peSubnetName
  }
}

// Private Endpoint for Azure Cognitive Search
module searchPrivateEndpoint '../network/private-endpoint.bicep' = [for privateDnsZoneName in privateDnsZoneNames: if ( private ) {
  name: privateDnsZoneName
  params: {
    privateDnsZoneName: privateDnsZoneName
    location: location
    tags: tags
    vnetId: existingVnet.id
    subnetId: existingVnet::existingsubnet.id
    privateEndpointName: 'pe-${name}-${privateDnsZoneName}'
    privateLinkServiceId: search.id
    privateLinkServicegroupId: 'searchService'
  }
}]
output id string = search.id
output endpoint string = 'https://${name}.search.windows.net/'
output name string = search.name
