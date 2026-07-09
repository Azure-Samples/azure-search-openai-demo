metadata description = 'Creates a Microsoft Foundry project inside an existing AIServices (Foundry) account, with optional project-scoped role assignments.'

// Why a custom module instead of AVM?
// The AVM account module (avm/res/cognitive-services/account) only exposes an
// `allowProjectManagement` flag, which turns the account into a Foundry account
// but does NOT create a project. As of avm/res/cognitive-services/account:0.15.0
// there is no parameter for a `Microsoft.CognitiveServices/accounts/projects`
// child resource, and no standalone AVM module for Foundry projects was published
// at implementation time. We need an actual project (to open in the new Foundry
// portal and to scope RBAC to), so this thin module declares the project resource
// directly and assigns roles at the project scope (the AVM `roleAssignments` param
// only assigns at the account scope). If AVM later ships a supported project
// module, this file can be replaced with it.

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

// Each element is an object of the shape:
//   { principalId: string, roleDefinitionId: string, principalType: 'User' | 'Group' | 'ServicePrincipal' }
// A plain `array` is used (rather than a user-defined type) on purpose: user-defined
// types force the compiled ARM template into symbolic-name mode (languageVersion 2.0),
// which makes the many same-named `existing` resource-group references in main.bicep
// collide during ARM validation ("resourceGroup ... is defined multiple times").
@description('Role assignments to create at the project scope.')
param roleAssignments array = []

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
