param keyVaultName string
param storeComputerVisionSecret bool
param computerVisionId string
param computerVisionSecretName string

module computerVisionKVSecret 'core/security/keyvault-secret.bicep' = if (storeComputerVisionSecret) {
  name: 'keyvault-secret'
  params: {
    keyVaultName: storeComputerVisionSecret ? keyVaultName : ''
    name: computerVisionSecretName
    secretValue: storeComputerVisionSecret ? listKeys(computerVisionId, '2023-05-01').key1 : ''
  }
}
