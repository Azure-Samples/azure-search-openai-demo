metadata description = 'Create a private endpoint for a given sub-resource, subnet, and private DNS zone group'

@description('The location for the private endpoint')
param location string

@description('The name of the private endpoint')
param name string

@description('The tags for the private endpoint')
param tags object = {}

@description('The ID of the resource to connect to')
param serviceId string

@description('The ID of the subnet to connect to')
param subnetId string

@description('The group ID of the sub-resource to connect to')
param groupIds array = []

@description('The ID of the private DNS zone to connect to')
param dnsZoneId string

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2021-02-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'privateLinkServiceConnection'
        properties: {
          privateLinkServiceId: serviceId
          groupIds: groupIds
        }
      }
    ]
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2020-06-01' = {
  parent: privateEndpoint
  name: '${name}-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

output name string = privateEndpoint.name
output id string = privateEndpoint.id
