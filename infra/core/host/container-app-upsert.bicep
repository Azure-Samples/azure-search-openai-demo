param name string
param location string = resourceGroup().location
param tags object = {}

param containerAppsEnvironmentName string
param containerName string = 'main'
param containerRegistryName string

@description('Minimum number of replicas to run')
@minValue(1)
param containerMinReplicas int = 1
@description('Maximum number of replicas to run')
@minValue(1)
param containerMaxReplicas int = 10

@description('The secrets required for the container')
@secure()
param secrets object = {}

@description('The environment variables for the container in key value pairs')
param env object = {}

@description('The environment variables with secret references')
param envSecrets array = []

param external bool = true
param targetPort int = 80
param exists bool

@description('User assigned identity name')
param identityName string

@description('Enabled Ingress for container app')
param ingressEnabled bool = true

// Dapr Options
@description('Enable Dapr')
param daprEnabled bool = false
@description('Dapr app ID')
param daprAppId string = containerName
@allowed([ 'http', 'grpc' ])
@description('Protocol used by Dapr to connect to the app, e.g. http or grpc')
param daprAppProtocol string = 'http'

@description('CPU cores allocated to a single container instance, e.g. 0.5')
param containerCpuCoreCount string = '0.5'

@description('Memory allocated to a single container instance, e.g. 1Gi')
param containerMemory string = '1.0Gi'

@description('Workload profile name to use for the container app when using private ingress')
param workloadProfileName string = 'Warm'

param allowedOrigins array = []

resource existingApp 'Microsoft.App/containerApps@2022-03-01' existing = if (exists) {
  name: name
}

var envAsArray = [
  for key in objectKeys(env): {
    name: key
    value: '${env[key]}'
  }
]

module app 'container-app.bicep' = {
  name: '${deployment().name}-update'
  params: {
    name: name
    location: location
    tags: tags
    identityName: identityName
    ingressEnabled: ingressEnabled
    containerName: containerName
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    containerCpuCoreCount: containerCpuCoreCount
    containerMemory: containerMemory
    containerMinReplicas: containerMinReplicas
    containerMaxReplicas: containerMaxReplicas
    daprEnabled: daprEnabled
    daprAppId: daprAppId
    daprAppProtocol: daprAppProtocol
    secrets: secrets
    allowedOrigins: allowedOrigins
    external: external
    env: concat(envAsArray, envSecrets)
    imageName: exists ? existingApp.properties.template.containers[0].image : ''
    targetPort: targetPort
  }
}

output defaultDomain string = app.outputs.defaultDomain
output imageName string = app.outputs.imageName
output name string = app.outputs.name
output uri string = app.outputs.uri
output identityResourceId string = app.outputs.identityResourceId
output identityPrincipalId string = app.outputs.identityPrincipalId
