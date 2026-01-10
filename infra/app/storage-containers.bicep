targetScope = 'resourceGroup'

@description('Name of existing storage account to add deployment containers to')
param storageAccountName string
@description('List of container names to ensure exist')
param containerNames array

// Existing storage account
resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Existing blob service
resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  name: 'default'
  parent: stg
}

// Create each container (no public access, default properties)
resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for c in containerNames: {
  name: c
  parent: blob
  properties: {}
}]
