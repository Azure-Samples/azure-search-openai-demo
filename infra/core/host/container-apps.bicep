metadata description = 'Creates an Azure Container Registry and an Azure Container Apps environment.'
param name string
param location string = resourceGroup().location
param tags object = {}

param containerAppsEnvironmentName string
param containerRegistryName string
param containerRegistryResourceGroupName string = ''
param containerRegistryAdminUserEnabled bool = false
param logAnalyticsWorkspaceResourceId string
param applicationInsightsName string = '' // Not used here, was used for DAPR
param virtualNetworkSubnetId string = ''
@allowed(['Consumption', 'D4', 'D8', 'D16', 'D32', 'E4', 'E8', 'E16', 'E32', 'NC24-A100', 'NC48-A100', 'NC96-A100'])
param workloadProfile string

var workloadProfiles = workloadProfile == 'Consumption'
  ? [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  : [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
      {
        minimumCount: 0
        maximumCount: 2
        name: workloadProfile
        workloadProfileType: workloadProfile
      }
    ]

@description('Optional user assigned identity IDs to assign to the resource')
param userAssignedIdentityResourceIds array = []

module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.8.0' = {
  name: '${name}-container-apps-environment'
  params: {
    // Required parameters
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId

    managedIdentities: empty(userAssignedIdentityResourceIds) ? {
      systemAssigned: true
    } : {
      userAssignedResourceIds: userAssignedIdentityResourceIds
    }

    name: containerAppsEnvironmentName
    // Non-required parameters
    infrastructureResourceGroupName: containerRegistryResourceGroupName
    infrastructureSubnetId: virtualNetworkSubnetId
    location: location
    tags: tags
    zoneRedundant: false
    workloadProfiles: workloadProfiles
  }
}

module containerRegistry 'br/public:avm/res/container-registry/registry:0.5.1' = {
  name: '${name}-container-registry'
  scope: !empty(containerRegistryResourceGroupName)
    ? resourceGroup(containerRegistryResourceGroupName)
    : resourceGroup()
  params: {
    name: containerRegistryName
    location: location
    acrAdminUserEnabled: containerRegistryAdminUserEnabled
    tags: tags
  }
}

output defaultDomain string = containerAppsEnvironment.outputs.defaultDomain
output environmentName string = containerAppsEnvironment.outputs.name
output environmentId string = containerAppsEnvironment.outputs.resourceId

output registryLoginServer string = containerRegistry.outputs.loginServer
output registryName string = containerRegistry.outputs.name
