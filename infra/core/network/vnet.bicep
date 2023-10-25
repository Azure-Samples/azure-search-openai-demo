param location string = resourceGroup().location
param tags object = {}

param vnetName string
param vnetAddressPrefix string = ''

param peSubnetName string
param peSubnetAddressPrefix string = ''

param acaSubnetName string
param acaSubnetAddressPrefix string = ''

resource vnet 'Microsoft.Network/virtualNetworks@2021-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: peSubnetName
        properties: {
          addressPrefix: peSubnetAddressPrefix
          //networkSecurityGroup: { id: nsg_default.id }
        }
      }
      {
        name: acaSubnetName
        properties: {
          addressPrefix: acaSubnetAddressPrefix
          //networkSecurityGroup: { id: nsg_default.id }
          
          delegations: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
          
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output subnetId string = filter(vnet.properties.subnets, (subnet) => subnet.name == peSubnetName)[0].id
output appSubnetId string = filter(vnet.properties.subnets, (subnet) => subnet.name == acaSubnetName)[0].id
