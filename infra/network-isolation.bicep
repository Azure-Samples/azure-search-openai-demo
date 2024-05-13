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

var abbrs = loadJsonContent('abbreviations.json')

resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' existing = {
  name: appServicePlanName
}

module vnet './core/networking/vnet.bicep' = {
  name: vnetName
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

module nic 'core/networking/nic.bicep' = if (provisionVm) {
  name: 'nic'
  params: {
    name: '${abbrs.networkNetworkInterfaces}${resourceToken}'
    location: location
    subnetId: vnet.outputs.vnetSubnets[3].id
  }
}

module publicIp 'core/networking/ip.bicep' = if (provisionVm) {
  name: 'ip'
  params: {
    name: '${abbrs.networkPublicIPAddresses}${resourceToken}'
    location: location
  }
}

module bastion 'core/networking/bastion.bicep' = if (provisionVm) {
  name: 'bastion'
  params: {
    name: '${abbrs.networkBastionHosts}${resourceToken}'
    location: location
    subnetId: vnet.outputs.vnetSubnets[1].id
    publicIPId: provisionVm ? publicIp.outputs.id : ''
  }
}

output appSubnetId string = vnet.outputs.vnetSubnets[2].id
output backendSubnetId string = vnet.outputs.vnetSubnets[0].id
output vnetName string = vnet.outputs.name
output nicId string = provisionVm ? nic.outputs.id : ''
