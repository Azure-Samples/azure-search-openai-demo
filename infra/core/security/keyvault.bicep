metadata description = 'Creates an Azure Key Vault.'
param name string
param location string = resourceGroup().location

// Allow public network access to Key Vault
param allowPublicNetworkAccess bool = false

// Allow all Azure services to bypass Key Vault network rules
param allowAzureServicesAccess bool = true

param networkAcls object = {
  bypass: allowAzureServicesAccess ? 'AzureServices' : 'None'
  defaultAction: allowPublicNetworkAccess ? 'Allow' : 'Deny'
  ipRules: []
  virtualNetworkRules: []
}
param tags object = {}

param principalId string = ''

resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enablePurgeProtection: true
    enableSoftDelete: true
    networkAcls: networkAcls
    accessPolicies: !empty(principalId) ? [
      {
        objectId: principalId
        permissions: { secrets: [ 'get', 'list' ] }
        tenantId: subscription().tenantId
      }
    ] : []
  }
}

output endpoint string = keyVault.properties.vaultUri
output name string = keyVault.name
