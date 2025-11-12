@description('Creates an Azure Key Vault for storing application secrets.')
param name string
param location string = resourceGroup().location
param tags object = {}
@description('Tenant ID for access policies')
param tenantId string
@description('Object IDs of users/principals that need access to Key Vault')
param accessPolicies array = []
@description('Enable soft delete (recommended for production)')
param enableSoftDelete bool = true
@description('Retention days for soft delete (7-90)')
param softDeleteRetentionInDays int = 7
@description('Enable purge protection (prevents permanent deletion)')
param enablePurgeProtection bool = false
@description('SKU for Key Vault (standard or premium)')
@allowed(['standard', 'premium'])
param sku string = 'standard'

// Key Vault access policies structure:
// {
//   objectId: string
//   tenantId: string
//   permissions: {
//     keys: array
//     secrets: array
//     certificates: array
//   }
// }

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: sku
    }
    enabledForDeployment: false
    enabledForTemplateDeployment: true // Allow Bicep/ARM templates to access secrets
    enabledForDiskEncryption: false
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection
    accessPolicies: accessPolicies
    networkAcls: {
      defaultAction: 'Allow' // Can be restricted to specific networks if needed
      bypass: 'AzureServices' // Allow Azure services to access
    }
    publicNetworkAccess: 'Enabled'
  }
}

output id string = keyVault.id
output name string = keyVault.name
output vaultUri string = keyVault.properties.vaultUri





