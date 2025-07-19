metadata name = 'DocumentDB Database Account SQL Role Assignments.'
metadata description = 'Assign RBAC role for data plane access to Azure Cosmos DB for NoSQL.'

@description('Name of the Azure Cosmos DB for NoSQL account.')
param databaseAccountName string

@description('Id of the identity/principal to assign this role in the context of the account.')
param principalId string = ''

@description('Id of the role definition to assign to the targeted principal in the context of the account.')
param roleDefinitionId string

resource databaseAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: databaseAccountName
}

resource sqlRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  name: guid(databaseAccount.id, principalId, roleDefinitionId)
  parent: databaseAccount
  properties: {
    principalId: principalId
    roleDefinitionId: roleDefinitionId
    scope: databaseAccount.id
  }
}

output sqlRoleAssignmentId string = sqlRoleAssignment.id
