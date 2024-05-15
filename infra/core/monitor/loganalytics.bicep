metadata description = 'Creates a Log Analytics workspace.'
param name string
param location string = resourceGroup().location
param tags object = {}
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccessForIngestion string = 'Enabled'
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccessForQuery string = 'Enabled'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2021-12-01-preview' = {
  name: name
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    features: {
      searchVersion: 1
    }
    sku: {
      name: 'PerGB2018'
    }
    publicNetworkAccessForIngestion: publicNetworkAccessForIngestion
    publicNetworkAccessForQuery: publicNetworkAccessForQuery
  }
}

output id string = logAnalytics.id
output name string = logAnalytics.name