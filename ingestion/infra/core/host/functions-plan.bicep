@description('Name of the App Service Plan')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('SKU for the App Service Plan')
param sku object = {
  name: 'Y1'
  tier: 'Dynamic'
}

resource plan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: name
  location: location
  tags: tags
  sku: sku
  properties: {
    reserved: true // Required for Linux
  }
}

output id string = plan.id
output name string = plan.name
