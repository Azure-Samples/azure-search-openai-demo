param keyVaultName string
param storeComputerVisionSecret bool
param computerVisionId string
param computerVisionSecretName string
param storeSearchServiceSecret bool
param searchServiceId string
param searchServiceSecretName string

module computerVisionKVSecret 'core/security/keyvault-secret.bicep' = if (storeComputerVisionSecret) {
  name: 'keyvault-secret'
  params: {
    keyVaultName: storeComputerVisionSecret ? keyVaultName : ''
    name: computerVisionSecretName
    secretValue: storeComputerVisionSecret ? listKeys(computerVisionId, '2023-05-01').key1 : ''
  }
}

module searchServiceKVSecret 'core/security/keyvault-secret.bicep' = if (storeSearchServiceSecret) {
  name: 'searchservice-secret'
  params: {
    keyVaultName: storeSearchServiceSecret ? keyVaultName : ''
    name: searchServiceSecretName
    secretValue: storeSearchServiceSecret ? listAdminKeys(searchServiceId, '2021-04-01-preview').primaryKey : ''
  }
}
