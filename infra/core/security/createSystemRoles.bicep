targetScope = 'subscription'

param principalId string
@allowed(['Device','ForeignGroup','Group','ServicePrincipal','User'])
param principalType string = 'ServicePrincipal'
param resourceToken string
param resourceGroupName string
param openAiResourceGroupName string = ''
param searchServiceResourceGroupName string = ''
param storageResourceGroupName string = ''

var roleDefinitions = loadJsonContent('roleDefinitions.json')

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroupName
}
resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : resourceGroupName
}
resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : resourceGroupName
}

resource openAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceToken, subscription().id, openAiResourceGroup.id, principalId, roleDefinitions.OpenAIUser)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.OpenAIUser)
  }
}
resource storageUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceToken, subscription().id, storageResourceGroup.id, principalId, roleDefinitions.StorageUser)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.StorageUser)
  }
}
resource searchUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceToken, subscription().id, searchServiceResourceGroup.id, principalId, roleDefinitions.SearchUser)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.SearchUser)
  }
}
