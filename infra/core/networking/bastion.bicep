param name string
param location string
param publicIPId string
param subnetId string

resource bastionHost 'Microsoft.Network/bastionHosts@2022-01-01' = {
  name: name
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'IpConf'
        properties: {
          subnet: {
            id: subnetId
          }
          publicIPAddress: {
            id: publicIPId
          }
        }
      }
    ]
  }
}