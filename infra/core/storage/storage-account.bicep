param name string
param location string = resourceGroup().location
param tags object = {}


@allowed([ 'Hot', 'Cool', 'Premium' ])
param accessTier string = 'Hot'
param allowBlobPublicAccess bool = false
param allowCrossTenantReplication bool = true
param allowSharedKeyAccess bool = true
param defaultToOAuthAuthentication bool = false
param deleteRetentionPolicy object = {}
@allowed([ 'AzureDnsZone', 'Standard' ])
param dnsEndpointType string = 'Standard'
param kind string = 'StorageV2'
param minimumTlsVersion string = 'TLS1_2'

//shoud be Disabled for closed environment. Set to Enabled and restrict access from specified address for convenience during the workshop
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Enabled'
param sku object = { name: 'Standard_LRS' }

param containers array = []

// parameters for private deployment
param private bool = false
param clientIpAddress string = ''
param vnetName string
param peSubnetName string
var privateDnsZoneNames = [
  'privatelink.blob.core.windows.net'
]

resource storage 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: sku
  properties: {
    accessTier: accessTier
    allowBlobPublicAccess: allowBlobPublicAccess
    allowCrossTenantReplication: allowCrossTenantReplication
    allowSharedKeyAccess: allowSharedKeyAccess
    defaultToOAuthAuthentication: defaultToOAuthAuthentication
    dnsEndpointType: dnsEndpointType
    minimumTlsVersion: minimumTlsVersion
    networkAcls: {
      bypass: 'AzureServices'
      // Allow access from the client PC
      defaultAction: (private) ? 'Deny' : 'Allow'
      ipRules: (private) ? [
        {
          action: 'Allow'
          value: clientIpAddress 
        }
      ] : []
    }
    publicNetworkAccess: publicNetworkAccess
  }

  resource blobServices 'blobServices' = if (!empty(containers)) {
    name: 'default'
    properties: {
      deleteRetentionPolicy: deleteRetentionPolicy
    }
    resource container 'containers' = [for container in containers: {
      name: container.name
      properties: {
        publicAccess: contains(container, 'publicAccess') ? container.publicAccess : 'None'
      }
    }]
  }
}

resource existingVnet 'Microsoft.Network/virtualNetworks@2020-05-01' existing = if ( private ) {
  name: vnetName
  resource existingsubnet 'subnets' existing = {
    name: peSubnetName
  }
}

// Private Endpoint for storage
module storagePrivateEndpoint '../network/private-endpoint.bicep' = [for privateDnsZoneName in privateDnsZoneNames: if ( private ) {
  name: privateDnsZoneName
  params: {
    privateDnsZoneName: privateDnsZoneName
    location: location
    tags: tags
    vnetId: existingVnet.id
    subnetId: existingVnet::existingsubnet.id
    privateEndpointName: 'pe-${name}-${privateDnsZoneName}'
    privateLinkServiceId: storage.id
    privateLinkServicegroupId: 'BLOB'
  }
}]
output name string = storage.name
output primaryEndpoints object = storage.properties.primaryEndpoints
output id string = storage.id
