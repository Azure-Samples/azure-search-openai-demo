metadata description = 'Sets up private networking for all resources, using VNet, private endpoints, and DNS zones.'

@description('The name of the VNet to create')
param vnetName string

@description('The location to create the VNet and private endpoints')
param location string = resourceGroup().location

@description('The tags to apply to all resources')
param tags object = {}

@description('The name of an existing App Service Plan to connect to the VNet')
param appServicePlanName string

@description('A unique token to append to the end of all resource names')
param resourceToken string

param provisionVm bool = false

param usePrivateEndpoint bool = false

var abbrs = loadJsonContent('abbreviations.json')

resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' existing = {
  name: appServicePlanName
}

module vnet './core/networking/vnet.bicep' = if (usePrivateEndpoint) {
  name: 'vnet'
  params: {
    name: vnetName
    location: location
    tags: tags
    subnets: [
      {
        name: 'backend-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'AzureBastionSubnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'app-int-subnet'
        properties: {
          addressPrefix: '10.0.3.0/24'
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegations: [
            {
              id: appServicePlan.id
              name: appServicePlan.name
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
      {
        name: 'vm-subnet'
        properties: {
          addressPrefix: '10.0.4.0/24'
        }
      }
    ]
  }
}

module nic 'core/networking/nic.bicep' = if (usePrivateEndpoint && provisionVm) {
  name: 'nic'
  params: {
    name: '${abbrs.networkNetworkInterfaces}${resourceToken}'
    location: location
    subnetId: usePrivateEndpoint ? vnet.outputs.vnetSubnets[3].id : ''
  }
}

module publicIp 'core/networking/ip.bicep' = if (usePrivateEndpoint && provisionVm) {
  name: 'ip'
  params: {
    name: '${abbrs.networkPublicIPAddresses}${resourceToken}'
    location: location
  }
}

module bastion 'core/networking/bastion.bicep' = if (usePrivateEndpoint && provisionVm) {
  name: 'bastion'
  params: {
    name: '${abbrs.networkBastionHosts}${resourceToken}'
    location: location
    subnetId: usePrivateEndpoint ? vnet.outputs.vnetSubnets[1].id : ''
    publicIPId: provisionVm ? publicIp.outputs.id : ''
  }
}

output appSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[2].id : ''
output backendSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[0].id : ''
output vnetName string = usePrivateEndpoint ? vnet.outputs.name : ''
output nicId string = provisionVm && usePrivateEndpoint ? nic.outputs.id : ''
