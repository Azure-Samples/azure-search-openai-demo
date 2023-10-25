param name string
param location string = resourceGroup().location
param tags object = {}

param adminUserEnabled bool = true
param anonymousPullEnabled bool = false
param dataEndpointEnabled bool = false
param encryption object = {
  status: 'disabled'
}
param networkRuleBypassOptions string = 'AzureServices'
//shoud be Disabled for closed environment. Set to Enabled for convenience during the demo/workshop
param publicNetworkAccess string = 'Enabled'
param sku object = private ? {  name: 'Premium'} : { name: 'Basic' }
param zoneRedundancy string = 'Disabled'

@description('The log analytics workspace id used for logging & monitoring')
param workspaceId string = ''

var privateDnsZoneNames = [
  'privatelink.azurecr.io'
]

// parameters for private deployment
param private bool = false
param clientIpAddress string = ''
param vnetName string
param peSubnetName string

// 2022-02-01-preview needed for anonymousPullEnabled
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2022-02-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: sku
  properties: ( private ) ? {
    adminUserEnabled: adminUserEnabled
    anonymousPullEnabled: anonymousPullEnabled
    dataEndpointEnabled: dataEndpointEnabled
    encryption: encryption
    networkRuleBypassOptions: networkRuleBypassOptions
    publicNetworkAccess: publicNetworkAccess
    zoneRedundancy: zoneRedundancy
    networkRuleSet: {
      defaultAction: 'Deny'
      ipRules: [
        {
          action: 'Allow'
          value: clientIpAddress 
        }
      ]
    } 
  } : {
    adminUserEnabled: adminUserEnabled
    anonymousPullEnabled: anonymousPullEnabled
    dataEndpointEnabled: dataEndpointEnabled
    encryption: encryption
    networkRuleBypassOptions: networkRuleBypassOptions
    publicNetworkAccess: publicNetworkAccess
    zoneRedundancy: zoneRedundancy
  }
}

// TODO: Update diagnostics to be its own module
// Blocking issue: https://github.com/Azure/bicep/issues/622
// Unable to pass in a `resource` scope or unable to use string interpolation in resource types
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(workspaceId)) {
  name: 'registry-diagnostics'
  scope: containerRegistry
  properties: {
    workspaceId: workspaceId
    logs: [
      {
        category: 'ContainerRegistryRepositoryEvents'
        enabled: true
      }
      {
        category: 'ContainerRegistryLoginEvents'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        timeGrain: 'PT1M'
      }
    ]
  }
}

resource existingVnet 'Microsoft.Network/virtualNetworks@2020-05-01' existing = if ( private ) {
  name: vnetName
  resource existingsubnet 'subnets' existing = {
    name: peSubnetName
  }
}

// Private Endpoint for container registry
module containerRegistryEndpoint '../network/private-endpoint.bicep' = [for privateDnsZoneName in privateDnsZoneNames: if ( private ) {
  name: privateDnsZoneName
  params: {
    privateDnsZoneName: privateDnsZoneName
    location: location
    tags: tags
    vnetId: existingVnet.id
    subnetId: existingVnet::existingsubnet.id
    privateEndpointName: 'pe-${name}-${privateDnsZoneName}'
    privateLinkServiceId: containerRegistry.id
    privateLinkServicegroupId: 'registry'
  }
}]

output loginServer string = containerRegistry.properties.loginServer
output name string = containerRegistry.name
