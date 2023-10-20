param location string
param name string
param tags object = {}
param appServicePlanName string
param appServicePlanId string

var addressPrefix = '10.0.0.0/16'

var subnets = [
  {
    name: 'ai-subnet'
    properties: {
      addressPrefix:'10.0.1.0/24'
      privateEndpointNetworkPolicies: 'Enabled'
      privateLinkServiceNetworkPolicies: 'Enabled'      
    }
  }
  {
    name: 'AzureBastionSubnet'
    properties: {
      addressPrefix:'10.0.2.0/24'
      privateEndpointNetworkPolicies: 'Enabled'
      privateLinkServiceNetworkPolicies: 'Enabled'      
    }
  }
  {
    name: 'app-int-subnet'
    properties: {
      addressPrefix:'10.0.3.0/24'
      privateEndpointNetworkPolicies: 'Enabled'
      privateLinkServiceNetworkPolicies: 'Enabled'
      delegations: [
        {
          id: appServicePlanId
          name: appServicePlanName
          properties: {
            serviceName: 'Microsoft.Web/serverFarms'
          }
        }
      ]   
    }
  }  
]

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

output subnets array = [for (name, i) in subnets :{
  subnets : vnet.properties.subnets[i]
}]

output subnetids array = [for (name, i) in subnets :{
  subnets : vnet.properties.subnets[i].id
}]


output id string = vnet.id
output name string = vnet.name

output aiSubId string = vnet.properties.subnets[0].id
output bastionSubId string = vnet.properties.subnets[1].id
output appIntSubId string = vnet.properties.subnets[2].id
