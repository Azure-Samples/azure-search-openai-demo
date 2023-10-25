param name string
param location string = resourceGroup().location
param tags object = {}

param private bool = false
param amplsName string
param publicNetworkAccess string = private ? 'Disabled' : 'Enabled'

var AMPLS_ASSOCIATION_NAME = 'amplsassociationAppinsights'


resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    //shoud be Disabled for closed environment. Set to Enabled for convenience during the workshop
    publicNetworkAccessForIngestion:publicNetworkAccess
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Deploy Azure Monitor Private Link Scopes association resource
resource existingampls 'Microsoft.Insights/privateLinkScopes@2021-07-01-preview' existing = if ( private ) {
  name: amplsName
}

resource amplsassociation 'Microsoft.Insights/privateLinkScopes/scopedResources@2021-07-01-preview' = if ( private ) {
  parent: existingampls
  name: AMPLS_ASSOCIATION_NAME
  properties: {
    linkedResourceId: applicationInsights.id
  }
}

output connectionString string = applicationInsights.properties.ConnectionString
output instrumentationKey string = applicationInsights.properties.InstrumentationKey
output name string = applicationInsights.name
