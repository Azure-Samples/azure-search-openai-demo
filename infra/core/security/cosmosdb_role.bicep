param principalId string
param cosmosDbAccountName string
param roleDefinitionId string

resource cosmosdb 'Microsoft.DocumentDB/databaseAccounts@2021-04-15' existing = {
  name: cosmosDbAccountName
}

resource sqlRoleDefinition 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2023-04-15' existing = {
  name: roleDefinitionId
  parent: cosmosdb
}

resource sqlRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  name: guid(roleDefinitionId, principalId, cosmosdb.id)
  parent: cosmosdb
  properties: {
    principalId: principalId
    scope: cosmosdb.id  
    roleDefinitionId: sqlRoleDefinition.id
  }
}
