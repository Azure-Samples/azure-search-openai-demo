param name string
param location string
param subnetId string

resource nic 'Microsoft.Network/networkInterfaces@2022-05-01' = {
  name: name
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: subnetId
          }
        }
      }
    ]
  }
}

output id string = nic.id