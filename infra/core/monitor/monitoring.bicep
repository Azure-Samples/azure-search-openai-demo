param location string = resourceGroup().location
param tags object = {}

param applicationInsightsName string
param logAnalyticsName string
param amplsName string

param private bool = false
param vnetName string = ''
param peSubnetName string = ''

module logAnalytics 'loganalytics.bicep' = {
  name: 'loganalytics'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
    private: private
    amplsName: AMPLS.name
  }
}

module applicationInsights 'applicationinsights.bicep' = {
  name: 'applicationinsights'
  params: {
    name: applicationInsightsName
    location: location
    tags: tags
    private: private 
    amplsName: AMPLS.name
  }
}

// Azure Monitor Private Link Scope
module AMPLS 'ampls.bicep' = if ( private ) {
  name: 'ampls'
  params: {
    name: amplsName
    location: location
    tags: tags
    vnetName: vnetName
    peSubnetName:  peSubnetName
  }
}

output applicationInsightsConnectionString string = applicationInsights.outputs.connectionString
output applicationInsightsInstrumentationKey string = applicationInsights.outputs.instrumentationKey
output applicationInsightsName string = applicationInsights.outputs.name
output logAnalyticsWorkspaceId string = logAnalytics.outputs.id
output logAnalyticsWorkspaceName string = logAnalytics.outputs.name
