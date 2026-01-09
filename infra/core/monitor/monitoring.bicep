metadata description = 'Creates an Application Insights instance and a Log Analytics workspace.'
param logAnalyticsName string
param applicationInsightsName string
param location string = resourceGroup().location
param tags object = {}
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Enabled'

module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.7.0' = {
  name: 'loganalytics'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
    publicNetworkAccessForIngestion: publicNetworkAccess
    publicNetworkAccessForQuery: publicNetworkAccess
    useResourcePermissions: true
  }
}

module applicationInsights 'br/public:avm/res/insights/component:0.4.1' = {
  name: 'applicationinsights'
  params: {
    name: applicationInsightsName
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.outputs.resourceId
    publicNetworkAccessForIngestion: publicNetworkAccess
    publicNetworkAccessForQuery: publicNetworkAccess
  }
}

output applicationInsightsConnectionString string = applicationInsights.outputs.connectionString
output applicationInsightsId string = applicationInsights.outputs.resourceId
output applicationInsightsInstrumentationKey string = applicationInsights.outputs.instrumentationKey
output applicationInsightsName string = applicationInsights.outputs.name
output logAnalyticsWorkspaceId string = logAnalytics.outputs.resourceId
output logAnalyticsWorkspaceName string = logAnalytics.outputs.name
