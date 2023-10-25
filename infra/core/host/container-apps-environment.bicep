param name string
param location string = resourceGroup().location
param tags object = {}

param daprEnabled bool = false
param logAnalyticsWorkspaceName string
param applicationInsightsName string

// parameters for private deployment
param private bool = false
param vnetName string
param acaSubnetName string

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    daprAIInstrumentationKey: daprEnabled && !empty(applicationInsightsName) ? applicationInsights.properties.InstrumentationKey : ''
    // Vnet Config for private deployment
    vnetConfiguration: private ? {
      infrastructureSubnetId: existingVnet::existingAcaSubnet.id
      internal: false
    } : null
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (daprEnabled && !empty(applicationInsightsName)){
  name: applicationInsightsName
}


resource existingVnet 'Microsoft.Network/virtualNetworks@2020-05-01' existing = if ( private ) {
  name: vnetName
  resource existingAcaSubnet 'subnets' existing = {
    name: acaSubnetName
  }
}

output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
output name string = containerAppsEnvironment.name
output id string = containerAppsEnvironment.id
