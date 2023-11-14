metadata description = 'Creates an Azure App Service in an existing Azure App Service plan.'
param name string
param location string = resourceGroup().location
param tags object = {}

// Reference Properties
param applicationInsightsName string = ''
param appServicePlanId string
param keyVaultName string = ''
param managedIdentity bool = !empty(keyVaultName)
param privateEndpointSubnetId string = ''
param useVnet bool = false

// Runtime Properties
@allowed([
  'dotnet', 'dotnetcore', 'dotnet-isolated', 'node', 'python', 'java', 'powershell', 'custom'
])
param runtimeName string
param runtimeNameAndVersion string = '${runtimeName}|${runtimeVersion}'
param runtimeVersion string

// Microsoft.Web/sites Properties
param kind string = 'app,linux'

// Microsoft.Web/sites/config
param allowedOrigins array = []
param alwaysOn bool = true
param appCommandLine string = ''
@secure()
param appSettings object = {}
param clientAffinityEnabled bool = false
param enableOryxBuild bool = contains(kind, 'linux')
param functionAppScaleLimit int = -1
param linuxFxVersion string = runtimeNameAndVersion
param minimumElasticInstanceCount int = -1
param numberOfWorkers int = -1
param scmDoBuildDuringDeployment bool = false
param use32BitWorkerProcess bool = false
param ftpsState string = 'FtpsOnly'
param healthCheckPath string = ''
param allowInboundNetworkRange string = ''

var coreConfig = {
  linuxFxVersion: linuxFxVersion
  alwaysOn: alwaysOn
  ftpsState: ftpsState
  appCommandLine: appCommandLine
  numberOfWorkers: numberOfWorkers != -1 ? numberOfWorkers : null
  minimumElasticInstanceCount: minimumElasticInstanceCount != -1 ? minimumElasticInstanceCount : null
  minTlsVersion: '1.2'
  use32BitWorkerProcess: use32BitWorkerProcess
  functionAppScaleLimit: functionAppScaleLimit != -1 ? functionAppScaleLimit : null
  healthCheckPath: healthCheckPath
  cors: {
    allowedOrigins: union([ 'https://portal.azure.com', 'https://ms.portal.azure.com' ], allowedOrigins)
  }
}

var coreConfigWithNetworkRules = union(
  !empty(allowInboundNetworkRange) ? {
    ipSecurityRestrictions: [
      {
        // If allowInboundNetworkRange contains a slash, it's already CIDR notation, otherwise append /32
        ipAddress: contains(allowInboundNetworkRange, '/') ? allowInboundNetworkRange : '${allowInboundNetworkRange}/32'
        action: 'Allow'
        tag: 'Default'
        priority: 100
        description: 'Allow specified network range'
      }, {
        ipAddress: 'Any'
        action: 'Deny'
        priority: 2147483647
        name: 'Deny all'
        description: 'Deny all access'
      }
    ]
    ipSecurityRestrictionsDefaultAction: 'Deny'
  } : {},
  coreConfig
)

var coreProperties = {
  serverFarmId: appServicePlanId
  siteConfig: coreConfigWithNetworkRules
  clientAffinityEnabled: clientAffinityEnabled
  httpsOnly: true
  vnetRouteAllEnabled: useVnet
}

var appServiceProperties = union(
  !empty(privateEndpointSubnetId) ? {
    virtualNetworkSubnetId: privateEndpointSubnetId
  } : {},
  coreProperties
)

resource appService 'Microsoft.Web/sites@2022-03-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: appServiceProperties
  identity: { type: managedIdentity ? 'SystemAssigned' : 'None' }

  resource configLogs 'config' = {
    name: 'logs'
    properties: {
      applicationLogs: { fileSystem: { level: 'Verbose' } }
      detailedErrorMessages: { enabled: true }
      failedRequestsTracing: { enabled: true }
      httpLogs: { fileSystem: { enabled: true, retentionInDays: 1, retentionInMb: 35 } }
    }
  }

  resource basicPublishingCredentialsPoliciesFtp 'basicPublishingCredentialsPolicies' = {
    name: 'ftp'
    properties: {
      allow: false
    }
  }

  resource basicPublishingCredentialsPoliciesScm 'basicPublishingCredentialsPolicies' = {
    name: 'scm'
    properties: {
      allow: false
    }
  }
}

module config 'appservice-appsettings.bicep' = if (!empty(appSettings)) {
  name: '${name}-appSettings'
  params: {
    name: appService.name
    appSettings: union(appSettings,
      {
        SCM_DO_BUILD_DURING_DEPLOYMENT: string(scmDoBuildDuringDeployment)
        ENABLE_ORYX_BUILD: string(enableOryxBuild)
      },
      runtimeName == 'python' && appCommandLine == '' ? { PYTHON_ENABLE_GUNICORN_MULTIWORKERS: 'true' } : {},
      !empty(applicationInsightsName) ? { APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString } : {},
      !empty(keyVaultName) ? { AZURE_KEY_VAULT_ENDPOINT: keyVault.properties.vaultUri } : {})
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' existing = if (!(empty(keyVaultName))) {
  name: keyVaultName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (!empty(applicationInsightsName)) {
  name: applicationInsightsName
}

output id string = appService.id
output identityPrincipalId string = managedIdentity ? appService.identity.principalId : ''
output name string = appService.name
output uri string = 'https://${appService.properties.defaultHostName}'
