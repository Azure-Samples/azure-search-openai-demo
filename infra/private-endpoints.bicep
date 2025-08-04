metadata description = 'Creates private endpoints for Azure services and configures Azure Monitor Private Link Scope with DNS zones for secure private networking.'

@description('The tags to apply to all resources')
param tags object = {}

@description('The name of an existing VNet')
param vnetName string

@description('The location to create the private endpoints')
param location string = resourceGroup().location

param vnetPeSubnetId string

@description('A formatted array of private endpoint connections containing the dns zone name, group id, and list of resource ids of Private Endpoints to create')
param privateEndpointConnections array

@description('A unique token to append to the end of all resource names')
param resourceToken string

@description('Ingestion access mode for Azure Monitor Private Link Scope')
@allowed([ 'PrivateOnly', 'Open' ])
param monitorIngestionAccessMode string = 'PrivateOnly'

@description('Query access mode for Azure Monitor Private Link Scope')
@allowed([ 'PrivateOnly', 'Open' ])
param monitorQueryAccessMode string = 'Open'

@description('Resource ID of Application Insights for Azure Monitor Private Link Scope')
param applicationInsightsId string

@description('Resource ID of Log Analytics Workspace for Azure Monitor Private Link Scope')
param logAnalyticsWorkspaceId string

var abbrs = loadJsonContent('abbreviations.json')

// DNS Zones
module dnsZones './core/networking/private-dns-zones.bicep' = [for (privateEndpointConnection, i) in privateEndpointConnections: {
  name: '${privateEndpointConnection.groupId}-${i}-dnszone'
  params: {
    dnsZoneName: privateEndpointConnection.dnsZoneName
    tags: tags
    virtualNetworkName: vnetName
  }
}]

// Private Endpoints
var privateEndpointInfo = [
  for (privateEndpointConnection, i) in privateEndpointConnections: map(privateEndpointConnection.resourceIds, resourceId => {
    dnsZoneIndex: i
    groupId: privateEndpointConnection.groupId
    name: last(split(resourceId, '/'))
    resourceId: resourceId
  })
]
module privateEndpoints './core/networking/private-endpoint.bicep' = [for privateEndpointInfo in flatten(privateEndpointInfo): {
  name: '${privateEndpointInfo.name}-privateendpoint'
  params: {
    location: location
    name: '${privateEndpointInfo.name}${abbrs.privateEndpoint}${resourceToken}'
    tags: tags
    subnetId: vnetPeSubnetId
    serviceId: privateEndpointInfo.resourceId
    groupIds: [ privateEndpointInfo.groupId ]
    dnsZoneId: dnsZones[privateEndpointInfo.dnsZoneIndex].outputs.id
  }
  dependsOn: [ dnsZones ]
}]

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
    virtualNetworkName: vnetName
  }
}]
// Get blob DNS zone index for monitor private link
var blobEndpointInfo = filter(flatten(privateEndpointInfo), info => info.groupId == 'blob')
// Assert that blob endpoints exist (required for this application)
var dnsZoneBlobIndex = blobEndpointInfo[0].dnsZoneIndex

// Azure Monitor Private Link Scope
// https://learn.microsoft.com/azure/azure-monitor/logs/private-link-security
resource monitorPrivateLinkScope 'microsoft.insights/privateLinkScopes@2021-07-01-preview' = {
  name: 'mpls${resourceToken}'
  location: 'global'
  tags: tags
  properties: {
    // https://learn.microsoft.com/azure/azure-monitor/logs/private-link-security#private-link-access-modes-private-only-vs-open
    // Uses Private Link to communicate with resources in the AMPLS, but also allows traffic to continue to other resources
    accessModeSettings: {
      ingestionAccessMode: monitorIngestionAccessMode
      queryAccessMode: monitorQueryAccessMode
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

// Private endpoint
module monitorPrivateEndpoint './core/networking/private-endpoint.bicep' = {
  name: 'monitor-privatendpoint'
  params: {
    name: 'monitor${abbrs.privateEndpoint}${resourceToken}'
    location: location
    tags: tags
    subnetId: vnetPeSubnetId
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
  dependsOn: [ monitorDnsZones, dnsZones ]
}
