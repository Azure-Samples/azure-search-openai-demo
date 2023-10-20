param location string
param name string
param tags object = {}
param serviceId string
param subnetId string
param groupIds array = []
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
        name: 'privatelinkServiceonnection'
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
  properties:{
    privateDnsZoneConfigs:[
      {
        name:'config1'
        properties:{
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

output name string = privateEndpoint.name
