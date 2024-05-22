param name string
param location string

resource publicIp 'Microsoft.Network/publicIPAddresses@2022-01-01' = {
  name: name
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

output id string = publicIp.id