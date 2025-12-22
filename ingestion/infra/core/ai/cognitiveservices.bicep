@description('Name of the Cognitive Services account')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('Kind of Cognitive Services account')
@allowed(['OpenAI', 'FormRecognizer', 'ComputerVision', 'CognitiveServices'])
param kind string = 'OpenAI'

@description('SKU for the Cognitive Services account')
param sku object = {
  name: 'S0'
}

@description('Deployments for OpenAI models')
param deployments array = []

@description('Whether to disable local authentication')
param disableLocalAuth bool = true

@description('Custom subdomain name')
param customSubDomainName string = name

resource account 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: {
    customSubDomainName: customSubDomainName
    disableLocalAuth: disableLocalAuth
    publicNetworkAccess: 'Enabled'
  }
  sku: sku
}

@batchSize(1)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = [for deployment in deployments: {
  parent: account
  name: deployment.name
  properties: {
    model: deployment.model
    raiPolicyName: deployment.?raiPolicyName
  }
  sku: deployment.?sku ?? {
    name: 'Standard'
    capacity: 10
  }
}]

output name string = account.name
output endpoint string = account.properties.endpoint
output id string = account.id
