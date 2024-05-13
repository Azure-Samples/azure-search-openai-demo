metadata description = 'Creates a private DNS zone and links it to an existing virtual network'

@description('The name of the private DNS zone')
param dnsZoneName string

@description('The name of the existing virtual network to link to the private DNS zone')
param virtualNetworkName string

@description('The tags to associate with the private DNS zone and VNet link')
param tags object = {}

resource vnet 'Microsoft.Network/virtualNetworks@2020-06-01' existing = {
  name: virtualNetworkName
}

resource dnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: dnsZoneName
  location: 'global'
  tags: tags
  dependsOn: [
    vnet
  ]
}

resource privateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  name: '${virtualNetworkName}-dnslink'
  parent: dnsZone
  location: 'global'
  tags: tags
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

output privateDnsZoneName string = dnsZone.name
output id string = dnsZone.id