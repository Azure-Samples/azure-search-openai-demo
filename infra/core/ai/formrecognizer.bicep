param name string
param location string = resourceGroup().location
param tags object = {}

param customSubDomainName string = name
param kind string = 'FormRecognizer'
param publicNetworkAccess string = 'Enabled'
param sku object = {
  name: 'S0'
}

resource account 'Microsoft.CognitiveServices/accounts@2022-10-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess
  }
  sku: sku
}

output endpoint string = account.properties.endpoint
output id string = account.id
output name string = account.name
