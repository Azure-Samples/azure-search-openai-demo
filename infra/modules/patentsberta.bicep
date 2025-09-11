param environmentName string
param location string
param containerAppsEnvironmentName string
param containerRegistryName string
@secure()
param patentsbertaApiKey string = ''
@description('Immutable image tag for deterministic deployments (e.g., v1.0.0-20241201)')
param imageTag string = 'v1.0.0'

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: containerAppsEnvironmentName
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource patentsbertaApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'patentsberta-${resourceToken}'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'patentsberta'
          image: '${containerRegistry.properties.loginServer}/patentsberta-embeddings:${imageTag}'
          env: [
            {
              name: 'PATENTSBERTA_API_KEY'
              value: patentsbertaApiKey
            }
          ]
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
          probes: [
            {
              type: 'readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Grant AcrPull permission to the container app's system-assigned identity
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, patentsbertaApp.id, 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull role
    principalId: patentsbertaApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output endpoint string = 'https://${patentsbertaApp.properties.configuration.ingress.fqdn}'
output name string = patentsbertaApp.name
