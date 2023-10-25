param name string
param location string = resourceGroup().location
param tags object = {}

param customSubDomainName string = name
param deployments array = []
param kind string = 'OpenAI'
//shoud be Disabled for closed environment. Set to Enabled for convenience during the demo/workshop
param publicNetworkAccess string = 'Enabled'
param sku object = {
  name: 'S0'
}
param private bool = false
param clientIpAddress string = ''
param vnetName string
param peSubnetName string
param privateDnsZoneNames array = []

resource account 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess
    //shoud be Disabled for closed environment. Set to Enabled for convenience during the demo/workshop
    networkAcls: {
      defaultAction: (private) ? 'Deny' : 'Allow'
      ipRules: (private) ? [
        {
          action: 'Allow'
          value: clientIpAddress 
        }
      ] : []
    }
  } 
  sku: sku
}

@batchSize(1)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [for deployment in deployments: {
  parent: account
  name: deployment.name
  properties: {
    model: deployment.model
    raiPolicyName: contains(deployment, 'raiPolicyName') ? deployment.raiPolicyName : null
  }
  sku: contains(deployment, 'sku') ? deployment.sku : {
    name: 'Standard'
    capacity: 20
  }
}]

resource existingVnet 'Microsoft.Network/virtualNetworks@2020-05-01' existing = if ( private ) {
  name: vnetName
  resource existingsubnet 'subnets' existing = {
    name: peSubnetName
  }
}

module PrivateEndpoint '../network/private-endpoint.bicep' = [for privateDnsZoneName in privateDnsZoneNames: if ( private ) {
  name: privateDnsZoneName
  params: {
    privateDnsZoneName: privateDnsZoneName
    location: location
    tags: tags
    vnetId: existingVnet.id
    subnetId: existingVnet::existingsubnet.id
    privateEndpointName: 'pe-${name}-${privateDnsZoneName}'
    privateLinkServiceId: account.id
    privateLinkServicegroupId: 'account'
  }
}]


output endpoint string = account.properties.endpoint
output id string = account.id
output name string = account.name
