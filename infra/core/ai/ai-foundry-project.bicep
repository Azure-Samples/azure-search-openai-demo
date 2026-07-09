metadata description = 'Creates a Microsoft Foundry project inside an existing AIServices (Foundry) account, with optional project-scoped role assignments.'

@description('Name of the existing AIServices (Foundry) account that will host the project.')
param accountName string

@description('Name of the Foundry project to create.')
param projectName string

@description('Display name for the Foundry project. Defaults to the project name.')
param projectDisplayName string = projectName

@description('Description for the Foundry project.')
param projectDescription string = 'Microsoft Foundry project for azure-search-openai-demo'

@description('Location for the Foundry project. Defaults to the account location.')
param location string = resourceGroup().location

@description('Tags to apply to the project.')
param tags object = {}

@description('Role assignments to create at the project scope.')
param roleAssignments roleAssignmentInfo[] = []

type roleAssignmentInfo = {
  @description('Principal (object) ID to grant the role to.')
  principalId: string
  @description('Role definition GUID (unqualified) to assign.')
  roleDefinitionId: string
  @description('Type of the principal being granted the role.')
  principalType: 'User' | 'Group' | 'ServicePrincipal'
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectDisplayName
    description: projectDescription
  }
}

resource projectRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleAssignment in roleAssignments: {
    name: guid(project.id, roleAssignment.principalId, roleAssignment.roleDefinitionId)
    scope: project
    properties: {
      principalId: roleAssignment.principalId
      principalType: roleAssignment.principalType
      roleDefinitionId: subscriptionResourceId(
        'Microsoft.Authorization/roleDefinitions',
        roleAssignment.roleDefinitionId
      )
    }
  }
]

output name string = project.name
output resourceId string = project.id
@description('Microsoft Foundry project endpoint, used by the Foundry / Agents SDKs.')
output endpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'
