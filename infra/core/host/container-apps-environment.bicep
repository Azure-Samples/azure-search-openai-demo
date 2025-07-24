param name string
param location string = resourceGroup().location
param tags object = {}

param daprEnabled bool = false
param logAnalyticsWorkspaceName string = ''
param applicationInsightsName string = ''

@description('Virtual network name for container apps environment.')
param vnetName string = ''
@description('Subnet name for container apps environment integration.')
param subnetName string = ''
param subnetResourceId string

param usePrivateIngress bool = true

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2025-02-02-preview' = {
  name: name
  location: location
  tags: tags
  properties: {
    // We can't use a conditional here due to an issue with the Container Apps ARM parsing
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    daprAIInstrumentationKey: daprEnabled && !empty(applicationInsightsName) ? applicationInsights.properties.InstrumentationKey : ''
    publicNetworkAccess: usePrivateIngress ? 'Disabled' : 'Enabled'
    vnetConfiguration: (!empty(vnetName) && !empty(subnetName)) ? {
      // Use proper subnet resource ID format
      infrastructureSubnetId: subnetResourceId
      internal: usePrivateIngress
    } : null
    // Configure workload profile for dedicated environment (not consumption)
    workloadProfiles: usePrivateIngress
    ? [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
      {
        name: 'Warm'
        workloadProfileType: 'D4'
        minimumCount: 1
        maximumCount: 3
      }
    ]
    : []
  }
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = if (!empty(logAnalyticsWorkspaceName)) {
  name: logAnalyticsWorkspaceName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (daprEnabled && !empty(applicationInsightsName)){
  name: applicationInsightsName
}

output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
output name string = containerAppsEnvironment.name
output resourceId string = containerAppsEnvironment.id
