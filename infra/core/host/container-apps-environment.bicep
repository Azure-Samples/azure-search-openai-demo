param name string
param location string = resourceGroup().location
param tags object = {}

param daprEnabled bool = false
param logAnalyticsWorkspaceName string = ''
param applicationInsightsName string = ''

param subnetResourceId string

param usePrivateIngress bool = true

@allowed(['Consumption', 'D4', 'D8', 'D16', 'D32', 'E4', 'E8', 'E16', 'E32', 'NC24-A100', 'NC48-A100', 'NC96-A100'])
param workloadProfile string

// Make sure that we are using a non-consumption workload profile for private endpoints
var finalWorkloadProfile = (usePrivateIngress && workloadProfile == 'Consumption') ? 'D4' : workloadProfile

var minimumCount = usePrivateIngress ? 1 : 0
var maximumCount = usePrivateIngress ? 3 : 2

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
    vnetConfiguration: usePrivateIngress ? {
      infrastructureSubnetId: subnetResourceId
      internal: true
    } : null
    workloadProfiles: usePrivateIngress
    ? [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
      {
        name: 'Warm'
        workloadProfileType: finalWorkloadProfile
        minimumCount: minimumCount
        maximumCount: maximumCount
      }
    ]
    : [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
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
