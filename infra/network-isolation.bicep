metadata description = 'Sets up private networking for all resources, using VNet, private endpoints, and DNS zones.'

@description('The name of the VNet to create')
param vnetName string

@description('The location to create the VNet and private endpoints')
param location string = resourceGroup().location

@description('The tags to apply to all resources')
param tags object = {}

param usePrivateEndpoint bool = false

@allowed(['appservice', 'containerapps'])
param deploymentTarget string

@description('The name of an existing App Service Plan to connect to the VNet')
param appServicePlanName string

@description('The name of an existing Container Apps Environment to connect to the VNet')
param containerAppsEnvName string

param deployVpnGateway bool = false

resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' existing = if (deploymentTarget == 'appservice') {
  name: appServicePlanName
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = if (deploymentTarget == 'containerapps') {
  name: containerAppsEnvName
}

// Always need this one
var backendSubnet =  {
        name: 'backend-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }

var appServiceSubnet = {
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

var containerAppsSubnet = {
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

var gatewaySubnet = {
    name: 'GatewaySubnet' // Required name for Gateway subnet
    properties: {
      addressPrefix: '10.0.255.0/27' // Using a /27 subnet size which is minimal required size for gateway subnet
    }
  }

var privateDnsResolverSubnet = {
    name: 'dns-resolver-subnet' // Dedicated subnet for Azure Private DNS Resolver
    properties: {
      addressPrefix: '10.0.11.0/28' // Original value kept as requested
      delegations: [
        {
          name: 'Microsoft.Network.dnsResolvers'
          properties: {
            serviceName: 'Microsoft.Network/dnsResolvers'
          }
        }
      ]
    }
  }

var subnets = union(
  [backendSubnet, deploymentTarget == 'appservice' ? appServiceSubnet : containerAppsSubnet],
  deployVpnGateway ? [gatewaySubnet, privateDnsResolverSubnet] : [])

module vnet './core/networking/vnet.bicep' = if (usePrivateEndpoint) {
  name: 'vnet'
  params: {
    name: vnetName
    location: location
    tags: tags
    subnets: subnets
  }
}

output appSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[1].id : ''
output appSubnetName string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[1].name : ''
output backendSubnetId string = usePrivateEndpoint ? vnet.outputs.vnetSubnets[0].id : ''
output privateDnsResolverSubnetId string = deployVpnGateway ? vnet.outputs.vnetSubnets[3].id : ''
output vnetName string = usePrivateEndpoint ? vnet.outputs.name : ''
output vnetId string = usePrivateEndpoint ? vnet.outputs.id : ''
