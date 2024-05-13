metadata description = 'Creates a virtual network with 3 subnets (for AI, Azure Bastion, App Service).'

@description('The location for the VNet')
param location string

@description('The name of the VNet')
param name string

@description('The tags for the VNet')
param tags object = {}

var addressPrefix = '10.0.0.0/16'

param subnets array

resource vnet 'Microsoft.Network/virtualNetworks@2021-02-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: subnets
  }
}

output subnets array = [for (name, i) in subnets: {
  subnets: vnet.properties.subnets[i]
}]

output subnetids array = [for (name, i) in subnets: {
  subnets: vnet.properties.subnets[i].id
}]

output id string = vnet.id
output name string = vnet.name
output vnetSubnets array = vnet.properties.subnets