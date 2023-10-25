param name string
param location string = resourceGroup().location
param tags object = {}

param containerAppsEnvironmentName string
param containerRegistryName string
param logAnalyticsWorkspaceName string
param applicationInsightsName string = ''

param private bool = false
param vnetName string
param peSubnetName string
param acaSubnetName string
param clientIpAddress string = ''

module containerAppsEnvironment 'container-apps-environment.bicep' = {
  name: '${name}-container-apps-environment'
  params: {
    name: containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
    private: private
    vnetName: vnetName
    acaSubnetName: acaSubnetName
  }
}

module containerRegistry 'container-registry.bicep' = {
  name: '${name}-container-registry'
  params: {
    name: containerRegistryName
    location: location
    tags: tags
    private: private
    clientIpAddress: clientIpAddress
    vnetName: vnetName
    peSubnetName: peSubnetName
  }
}

output defaultDomain string = containerAppsEnvironment.outputs.defaultDomain
output environmentName string = containerAppsEnvironment.outputs.name
output environmentId string = containerAppsEnvironment.outputs.id
output registryLoginServer string = containerRegistry.outputs.loginServer
output registryName string = containerRegistry.outputs.name
