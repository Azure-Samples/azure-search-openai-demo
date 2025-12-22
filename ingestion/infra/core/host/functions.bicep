@description('Name of the Function App')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('App Service Plan ID')
param appServicePlanId string

@description('Runtime name (python, node, dotnet)')
param runtimeName string = 'python'

@description('Runtime version')
param runtimeVersion string = '3.11'

@description('Storage account name for the Function App')
param storageAccountName string

@description('Identity type')
@allowed(['None', 'SystemAssigned', 'UserAssigned'])
param identityType string = 'SystemAssigned'

@description('User-assigned identity ID')
param identityId string = ''

@description('App settings as array of name/value pairs')
param appSettings array = []

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' existing = {
  name: storageAccountName
}

resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: identityType == 'UserAssigned' ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  } : {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlanId
    siteConfig: {
      linuxFxVersion: '${toUpper(runtimeName)}|${runtimeVersion}'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

resource functionAppSettings 'Microsoft.Web/sites/config@2022-09-01' = {
  parent: functionApp
  name: 'appsettings'
  properties: union({
    AzureWebJobsStorage: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
    FUNCTIONS_EXTENSION_VERSION: '~4'
    FUNCTIONS_WORKER_RUNTIME: runtimeName
    WEBSITE_RUN_FROM_PACKAGE: '1'
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
  }, reduce(appSettings, {}, (cur, next) => union(cur, { '${next.name}': next.value })))
}

output id string = functionApp.id
output name string = functionApp.name
output uri string = functionApp.properties.defaultHostName
output identityPrincipalId string = identityType == 'SystemAssigned' ? functionApp.identity.principalId : ''
