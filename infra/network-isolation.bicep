metadata description = 'Sets up private networking for all resources, using VNet, private endpoints, and DNS zones.'

@description('The name of the VNet to create')
param vnetName string

@description('The location to create the VNet and private endpoints')
param location string = resourceGroup().location

@description('The tags to apply to all resources')
param tags object = {}

@description('The name of an existing App Service Plan to connect to the VNet')
param appServicePlanName string

@description('A formatted array of private endpoint connections containing the dns zone name, group id, and list of resource ids of Private Endpoints to create')
param privateEndpointConnections array

@description('Resource ID of Application Insights for Azure Monitor Private Link Scope')
param applicationInsightsId string

@description('Resource ID of Log Analytics Workspace for Azure Monitor Private Link Scope')
param logAnalyticsWorkspaceId string

@description('A unique token to append to the end of all resource names')
param resourceToken string

@description('Name of the search service')
param searchServiceName string

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
    ]
  }
}

// DNS Zones
module dnsZones './core/networking/private-dns-zones.bicep' = [for privateEndpointConnection in privateEndpointConnections: {
  name: '${privateEndpointConnection.groupId}-dnszone'
  params: {
    dnsZoneName: privateEndpointConnection.dnsZoneName
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}]

// Private Endpoints
var privateEndpointInfo = [
  for (privateEndpointConnection, i) in privateEndpointConnections: map(privateEndpointConnection.resourceIds, resourceId => {
    dnsZoneIndex: i
    groupId: privateEndpointConnection.groupId
    name: last(split(privateEndpointConnection.resourceId, '/'))
    resourceId: resourceId
  })
]
module privateEndpoints './core/networking/private-endpoint.bicep' = [for privateEndpointInfo in flatten(privateEndpointInfo): {
  name: '${privateEndpointInfo.name}-privateendpoint'
  params: {
    location: location
    name: '${privateEndpointInfo.name}${abbrs.privateEndpoint}${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.vnetSubnets[0].id
    serviceId: privateEndpointInfo.resourceId
    groupIds: [ privateEndpointInfo.groupId ]
    dnsZoneId: dnsZones[privateEndpointInfo.dnsZoneIndex].outputs.id
  }
}]


// Azure Monitor Private Link Scope
// https://learn.microsoft.com/en-us/azure/azure-monitor/logs/private-link-security
resource monitorPrivateLinkScope 'microsoft.insights/privateLinkScopes@2021-07-01-preview' = {
  name: 'mpls${resourceToken}'
  location: location
  tags: tags
  properties: {
    // https://learn.microsoft.com/azure/azure-monitor/logs/private-link-security#private-link-access-modes-private-only-vs-open
    // Uses Private Link to communicate with resources in the AMPLS, but also allows traffic to continue to other resources
    accessModeSettings: {
      ingestionAccessMode: 'PrivateOnly'
      queryAccessMode: 'PrivateOnly'
    }
  }

  resource logAnalyticsScopedResource 'scopedResources@2021-07-01-preview' = {
    name: 'log-analytics-workspace-scoped-resource'
    properties: {
      linkedResourceId: logAnalyticsWorkspaceId
    }
  }

  resource applicationInsightsScopedResource 'scopedResources@2021-07-01-preview' = {
    name: 'application-insights-scoped-resource'
    properties: {
      linkedResourceId: applicationInsightsId
    }
  }
}

// Provision additional DNS Zones for Azure Monitor
// https://learn.microsoft.com/azure/azure-monitor/logs/private-link-configure#review-your-endpoints-dns-settings
var monitorDnsZoneNames = [
  'privatelink.monitor.azure.com'
  'privatelink.oms.opinsights.azure.com'
  'privatelink.ods.opinsights.azure.com'
  'privatelink.agentsvc.azure.automation.net'
]
module monitorDnsZones './core/networking/private-dns-zones.bicep' = [for monitorDnsZoneName in monitorDnsZoneNames: {
  name: '${split(monitorDnsZoneName, '.')[1]}-dnszone'
  params: {
    dnsZoneName: monitorDnsZoneName
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}]
// Get blob DNS zone index for monitor private link
var dnsZoneBlobIndex = filter(flatten(privateEndpointInfo), info => info.groupId == 'blob')[0].dnsZoneIndex

// Private endpoint 
module monitorPrivateEndpoint './core/networking/private-endpoint.bicep' = {
  name: 'monitor-privatendpoint'
  params: {
    name: 'monitor${abbrs.privateEndpoint}${resourceToken}'
    location: location
    tags: tags
    subnetId: vnet.outputs.vnetSubnets[0].id
    serviceId: monitorPrivateLinkScope.id
    groupIds: [ 'azuremonitor' ]
    // Add multiple DNS zone configs for Azure Monitor
    privateDnsZoneConfigs: [
      {
        name: monitorDnsZones[0].name
        properties: {
          privateDnsZoneId: monitorDnsZones[0].outputs.id
        }
      }
      {
        name: monitorDnsZones[1].name
        properties: {
          privateDnsZoneId: monitorDnsZones[1].outputs.id
        }
      }
      {
        name: monitorDnsZones[2].name
        properties: {
          privateDnsZoneId: monitorDnsZones[2].outputs.id
        }
      }
      {
        name: monitorDnsZones[3].name
        properties: {
          privateDnsZoneId: monitorDnsZones[3].outputs.id
        }
      }
      {
        name: dnsZones[dnsZoneBlobIndex].name
        properties: {
          privateDnsZoneId: dnsZones[dnsZoneBlobIndex].outputs.id
        }
      }
    ]
  }
}

// Create search shared private links for all storage accounts (blob)
var searchBlobSharedPrivateLinkInfo = filter(flatten(privateEndpointInfo), info => info.groupId == 'blob')
module searchBlobSharedPrivateLink './core/search/search-private-link.bicep' = [for info in searchBlobSharedPrivateLinkInfo: {
  name: '${info.name}-search-shared-private-link'
  params: {
    name: '${info.name}${abbrs.privateLink}${resourceToken}'
    groupId: info.groupId
    searchName: searchServiceName
    resourceId: info.resourceId
  }
}]

output appSubnetId string = vnet.outputs.vnetSubnets[2].id
output vnetName string = vnet.outputs.name
