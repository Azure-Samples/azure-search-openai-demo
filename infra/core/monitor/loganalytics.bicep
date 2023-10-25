param name string
param location string = resourceGroup().location
param tags object = {}

param private bool = false
param amplsName string
param publicNetworkAccess string = private ? 'Disabled' : 'Enabled'

var AMPLS_ASSOCIATION_NAME = 'amplsassociationLogAnalytics'



resource existingampls 'Microsoft.Insights/privateLinkScopes@2021-07-01-preview' existing = if ( private ) {
  name: amplsName
}

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
    //shoud be Disabled for closed environment. Set to Enabled for convenience during the workshop
    publicNetworkAccessForIngestion: publicNetworkAccess
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Deploy Azure Monitor Private Link Scopes association resource
resource amplsassociation 'Microsoft.Insights/privateLinkScopes/scopedResources@2021-07-01-preview' = if ( private ) {
  parent: existingampls
  name: AMPLS_ASSOCIATION_NAME
  properties: {
    linkedResourceId: logAnalytics.id
  }
}

output id string = logAnalytics.id
output name string = logAnalytics.name
