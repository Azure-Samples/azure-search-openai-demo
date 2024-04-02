param keyVaultName string
param storeSearchServiceSecret bool
param searchServiceId string
param searchServiceSecretName string


module searchServiceKVSecret 'core/security/keyvault-secret.bicep' = if (storeSearchServiceSecret) {
  name: 'searchservice-secret'
  params: {
    keyVaultName: storeSearchServiceSecret ? keyVaultName : ''
    name: searchServiceSecretName
    secretValue: storeSearchServiceSecret ? listAdminKeys(searchServiceId, '2021-04-01-preview').primaryKey : ''
  }
}
