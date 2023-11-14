metadata description = 'Sets up private networking for all resources, using VNet, private endpoints, and DNS zones.'

@description('The name of the VNet to create')
param vnetName string

@description('The location to create the VNet and private endpoints')
param location string = resourceGroup().location

@description('The tags to apply to all resources')
param tags object = {}

@description('The ID of an existing App Service Plan to connect to the VNet')
param appServicePlanId string

@description('The name of an existing App Service Plan to connect to the VNet')
param appServicePlanName string

@description('The ID of an existing Storage Account to connect to the VNet')
param storageAccountId string

@description('The ID of an existing Search Service to connect to the VNet')
param searchServiceId string

@description('The ID of an existing Open AI resource to connect to the VNet')
param openAiId string

@description('The ID of an existing Form Recognizer resource to connect to the VNet')
param formRecognizerId string

@description('The name of an existing Search Service to connect to the VNet')
param searchServiceName string

@description('A unique token to append to the end of all resource names')
param resourceToken string

var environmentData = environment()
var abbrs = loadJsonContent('abbreviations.json')

module vnet './core/networking/vnet.bicep' = {
  name: vnetName
  params: {
    name: vnetName
    location: location
    tags: tags
    appServicePlanId: appServicePlanId
    appServicePlanName: appServicePlanName
  }
}

// DNSs Zones

module blobDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'blob-dnzones'
  params: {
    dnsZoneName: 'privatelink.blob.${environmentData.suffixes.storage}'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module documentsDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'documents-dnzones'
  params: {
    dnsZoneName: 'privatelink.documents.azure.com'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module vaultDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'vault-dnzones'
  params: {
    dnsZoneName: 'privatelink.vaultcore.azure.net'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module websitesDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'websites-dnzones'
  params: {
    dnsZoneName: 'privatelink.azurewebsites.net'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module cognitiveservicesDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'cognitiveservices-dnzones'
  params: {
    dnsZoneName: 'privatelink.cognitiveservices.azure.com'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module openaiDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'openai-dnzones'
  params: {
    dnsZoneName: 'privatelink.openai.azure.com'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module searchDnsZone './core/networking/private-dns-zones.bicep' = {
  name: 'searchs-dnzones'
  params: {
    dnsZoneName: 'privatelink.search.windows.net'
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}

module storagePrivateEndpoint './core/networking/private-endpoint.bicep' = {
  name: 'storageprivateendpoint'
  params: {
    location: location
    name: '${abbrs.storageStorageAccounts}${abbrs.privateEndpoint}${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: storageAccountId
    groupIds: [ 'blob' ]
    dnsZoneId: blobDnsZone.outputs.id
  }
}

module openAiPrivateEndpoint './core/networking/private-endpoint.bicep' = {
  name: 'openaiprivateendpoint'
  params: {
    location: location
    name: '${abbrs.cognitiveServicesAccounts}${abbrs.privateEndpoint}${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: openAiId
    groupIds: [ 'account' ]
    dnsZoneId: openaiDnsZone.outputs.id
  }
}

module formRecognizerPrivateEndpoint './core/networking/private-endpoint.bicep' = {
  name: 'formrecognizerprivateendpoint'
  params: {
    location: location
    name: '${abbrs.cognitiveServicesFormRecognizer}${abbrs.privateEndpoint}${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: formRecognizerId
    groupIds: [ 'account' ]
    dnsZoneId: cognitiveservicesDnsZone.outputs.id
  }
}

module searchStoragePrivateLink 'core/search/search-private-link.bicep' = {
  name: 'searchstorageprivatelink'
  params: {
    name: '${abbrs.searchSearchServices}${abbrs.privateLink}${abbrs.storageStorageAccounts}${resourceToken}'
    searchName: searchServiceName
    resourceId: storageAccountId
    groupId: 'blob'
  }
}

module searchPrivateEndpoint './core/networking/private-endpoint.bicep' = {
  name: 'searchprivateendpoint'
  params: {
    location: location
    name: '${abbrs.searchSearchServices}${abbrs.privateEndpoint}${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: searchServiceId
    groupIds: [ 'searchService' ]
    dnsZoneId: searchDnsZone.outputs.id
  }
}

output appSubnetId string = vnet.outputs.appIntSubId
output vnetName string = vnet.outputs.name
