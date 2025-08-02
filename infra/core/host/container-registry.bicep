param name string
param location string = resourceGroup().location
param tags object = {}

param adminUserEnabled bool = false
param anonymousPullEnabled bool = false
param dataEndpointEnabled bool = false
param encryption object = {
  status: 'disabled'
}
param networkRuleBypassOptions string = 'AzureServices'
param publicNetworkAccess string = useVnet ? 'Disabled' : 'Enabled' // Public network access is disabled if VNet integration is enabled
param useVnet bool = false // Determines if VNet integration is enabled
param sku object = {
  name: useVnet ? 'Premium' : 'Standard' // Use Premium if VNet is required, otherwise Standard
}
param zoneRedundancy string = 'Disabled'

// 2022-02-01-preview needed for anonymousPullEnabled
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2022-02-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: sku
  properties: {
    adminUserEnabled: adminUserEnabled
    anonymousPullEnabled: anonymousPullEnabled
    dataEndpointEnabled: dataEndpointEnabled
    encryption: encryption
    networkRuleBypassOptions: networkRuleBypassOptions
    publicNetworkAccess: publicNetworkAccess
    zoneRedundancy: zoneRedundancy
  }
}

output loginServer string = containerRegistry.properties.loginServer
output name string = containerRegistry.name
output resourceId string = containerRegistry.id
