param name string
param location string = resourceGroup().location
param tags object = {}
param pridnszonelist array = [
  'monitor.azure.com'
  'oms.opinsights.azure.com'
  'ods.opinsights.azure.com'
  'agentsvc.azure-automation.net'
  'blob.windows.core.net'
]
param vnetName string
param peSubnetName string

// AMPLS/Private Endpoint/Private DNS Zone variables
var privateEndpointeName = 'pe-ampls'
var privateLinkServiceName = 'pls-ampls'
var privateDNSZoneName = 'zonegroup-poc-main-stag-001'

resource existingVnet 'Microsoft.Network/virtualNetworks@2020-05-01' existing = {
  name: vnetName
  resource existingsubnet 'subnets' existing = {
    name: peSubnetName
  }
}

// Azure Monitor Private Link Scope
resource ampls 'microsoft.insights/privateLinkScopes@2021-07-01-preview' = {
  name: name
  location: 'global'
  tags: tags
  properties: {
    accessModeSettings: {
      ingestionAccessMode: 'PrivateOnly' // PrivateOnly, Open
      queryAccessMode: 'Open'
    }
  }
}

// Deploy Private Endpoint resource
resource peampls 'Microsoft.Network/privateEndpoints@2022-09-01' = {
  name: privateEndpointeName
  location: location
  tags: tags
  properties: {
    subnet: {
      id: existingVnet::existingsubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: privateLinkServiceName
        properties: {
          privateLinkServiceId: ampls.id
          groupIds: [
            'AzureMonitor'
          ]
        }
      }
    ]
  }
}

// Deploy Private DNS Zone resource
resource pridnszoneforampls 'Microsoft.Network/privateDnsZones@2020-06-01' = [for pridnszone in pridnszonelist: {
  name: 'privatelink.${pridnszone}'
  location: 'global'
  tags: tags
  properties: {
  }
}]

// Deploy Private DNS Zone Group resource
resource pridnszoneforamplsgroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2022-09-01' = {
  parent: peampls
  name: privateDNSZoneName
  properties: {
    privateDnsZoneConfigs: [
      {
        name: pridnszoneforampls[0].name
        properties: {
          privateDnsZoneId: pridnszoneforampls[0].id
        }
      }
      {
        name: pridnszoneforampls[1].name
        properties: {
          privateDnsZoneId: pridnszoneforampls[1].id
        }
      }
      {
        name: pridnszoneforampls[2].name
        properties: {
          privateDnsZoneId: pridnszoneforampls[2].id
        }
      }
      {
        name: pridnszoneforampls[3].name
        properties: {
          privateDnsZoneId: pridnszoneforampls[3].id
        }
      }
      {
        name: pridnszoneforampls[4].name
        properties: {
          privateDnsZoneId: pridnszoneforampls[4].id
        }
      }
    ]
  }
}

output amplsName string = ampls.name
output peAmplsName string = peampls.name
