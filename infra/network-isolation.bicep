param vnetName string
param location string = resourceGroup().location
param tags object = {}

param appServicePlanId string
param appServicePlanName string
param storageAccountId string
param searchServiceId string
param openAiId string
param formRecognizerId string
param searchServiceName string
param resourceToken string

var environmentData = environment()

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

module searchDnsZone './core/networking/private-dns-zones.bicep' =  {
  name: 'searchs-dnzones'
  params: {
    dnsZoneName: 'privatelink.search.windows.net' 
    tags: tags
    virtualNetworkName: vnet.outputs.name
  }
}


module storagepe './core/networking/private-endpoint.bicep' = {
  name: 'storagepe'
  params: {
    location: location
    name:'stragpe0${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: storageAccountId
    groupIds: ['blob']
    dnsZoneId: blobDnsZone.outputs.id
  }
}

module openAiPe './core/networking/private-endpoint.bicep' = {
  name: 'openAiPe'
  params: {
    location: location
    name: 'openAiPe${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: openAiId
    groupIds: ['account']
    dnsZoneId: openaiDnsZone.outputs.id
  }
}

module formRecognizerPe './core/networking/private-endpoint.bicep' = {
  name: 'formRecognizerPe'
  params: {
    location: location
    name: 'formRecognizerPe${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: formRecognizerId
    groupIds: ['account']
    dnsZoneId: cognitiveservicesDnsZone.outputs.id
  }
}

module searchStoragePrivatelink 'core/search/search-private-link.bicep' = {
  name: 'searchStoragePrivatelink'
  params: {
   name: '${searchServiceName}-storagelink'
   searchName: searchServiceName
   resourceId: storageAccountId
   groupId: 'blob'
  }
}

module searchPe './core/networking/private-endpoint.bicep' = {
  name: 'searchPe'
  params: {
    location: location
    name: 'searchPe${resourceToken}'
    tags: tags
    subnetId: vnet.outputs.aiSubId
    serviceId: searchServiceId
    groupIds: ['searchService']
    dnsZoneId: searchDnsZone.outputs.id
  }
}

output appSubnetId string = vnet.outputs.appIntSubId
output vnetName string = vnet.outputs.name
