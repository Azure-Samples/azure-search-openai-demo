metadata description = 'Sets up private networking for all resources, using VNet, private endpoints, and DNS zones.'

@description('The name of the VNet to create')
param vnetName string

@description('The location to create the VNet and private endpoints')
param location string = resourceGroup().location

@description('The tags to apply to all resources')
param tags object = {}

param usePrivateEndpoint bool = false

param containerAppsEnvName string

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: containerAppsEnvName
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
      { // App Service / Container Apps specific subnet
        name: 'app-int-subnet'
        properties: {
          addressPrefix: '10.0.4.0/23'
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegations: [
            {
              id: containerAppsEnvironment.id
              name: containerAppsEnvironment.name
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


output appSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[1].id : ''
output backendSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[0].id : ''
output bastionSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[2].id : ''
output vmSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[3].id : ''
output vnetName string = usePrivateEndpoint ? vnet.outputs.name : ''
