metadata description = 'Deploys an Azure Monitor Health Model with a dedicated managed identity, conditional entities based on deployed resources, and a use-case-driven entity hierarchy.'

// ── Parameters ──

@description('Name of the health model resource.')
param name string

@description('Azure region for the health model.')
param location string

@description('Resource tags.')
param tags object = {}

// Feature flags — control which entities and signals are created
@description('Deployment target: containerapps or appservice.')
param deploymentTarget string

@description('Whether Azure OpenAI is deployed.')
param deployAzureOpenAi bool

@description('Whether Application Insights and Log Analytics are deployed.')
param useApplicationInsights bool

@description('Whether Azure Speech output is enabled.')
param useSpeechOutputAzure bool = false

@description('Whether authentication with Cosmos DB chat history is enabled.')
param useAuthenticationWithCosmos bool = false

// Resource IDs — only required when corresponding feature flag is true
@description('Resource ID of the Container App (required when deploymentTarget is containerapps).')
param containerAppResourceId string = ''

@description('Resource ID of the App Service (required when deploymentTarget is appservice).')
param appServiceResourceId string = ''

@description('Resource ID of the Container Apps Managed Environment (required when deploymentTarget is containerapps).')
param managedEnvironmentResourceId string = ''

@description('Resource ID of the Cognitive Services account (Azure OpenAI). Required when deployAzureOpenAi is true.')
param cognitiveServicesResourceId string = ''

@description('Resource ID of the Azure AI Search service.')
param searchServiceResourceId string

@description('Resource ID of the Storage Account.')
param storageAccountResourceId string

@description('Resource ID of the Application Insights component. Required when useApplicationInsights is true.')
param applicationInsightsResourceId string = ''

@description('Resource ID of the Azure Speech service. Required when useSpeechOutputAzure is true.')
param speechServiceResourceId string = ''

@description('Resource ID of the Cosmos DB account. Required when useAuthenticationWithCosmos is true.')
param cosmosDbResourceId string = ''

@description('Resource ID of the Document Intelligence (Form Recognizer) Cognitive Services account.')
param documentIntelligenceResourceId string

// Computed flags
var isContainerApps = deploymentTarget == 'containerapps'
var isAppService = deploymentTarget == 'appservice'

// ── Canvas Layout ──
// Entities are arranged in 3 rows: root (Y=0), groups (Y=200), leaves (Y=400).
// Each group's X position = previous group's X + (number of children in previous group * spacing).
// Conditional groups (Speech, Auth) contribute 0 width when disabled.

@description('Horizontal spacing between leaf entities in the health model canvas (pixels).')
param canvasLeafSpacing int = 250

@description('Vertical position for group-level entities in the health model canvas.')
param canvasGroupRow int = 200

@description('Vertical position for leaf-level entities in the health model canvas.')
param canvasLeafRow int = 400

// Child counts per group (0 when the group is conditionally disabled)
var ragChatChildCount = 2 + (deployAzureOpenAi ? 1 : 0) + (useApplicationInsights ? 1 : 0)  // KnowledgeSearch + BackendApp + AIInference? + AppPerf?
var docIngestionChildCount = 2                                                                 // DocStorage + DocIntelligence
var speechChildCount = useSpeechOutputAzure ? 1 : 0                                            // SpeechService
var authHistoryChildCount = useAuthenticationWithCosmos ? 1 : 0                                 // CosmosDB
var platformChildCount = isContainerApps ? 1 : 0                                               // ContainerPlatform

// Group X positions: tightly packed, each starts after the previous group's children
var xRagChat = 0
var xDocIngestion = xRagChat + ragChatChildCount * canvasLeafSpacing
var xSpeech = xDocIngestion + docIngestionChildCount * canvasLeafSpacing
var xAuthHistory = xSpeech + speechChildCount * canvasLeafSpacing
var xPlatform = xAuthHistory + authHistoryChildCount * canvasLeafSpacing
var xObservability = xPlatform + platformChildCount * canvasLeafSpacing

// ── Dedicated Managed Identity ──

resource healthModelIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-identity'
  location: location
  tags: tags
}

// Monitoring Reader role (43d0d8ad-25c7-4714-9337-8ba259a9fe05)
resource monitoringReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, resourceGroup().id, healthModelIdentity.id, '43d0d8ad-25c7-4714-9337-8ba259a9fe05')
  properties: {
    principalId: healthModelIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '43d0d8ad-25c7-4714-9337-8ba259a9fe05')
  }
}

// Reader role (acdd72a7-3385-48ef-bd42-f606fba81ae7)
resource readerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, resourceGroup().id, healthModelIdentity.id, 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
  properties: {
    principalId: healthModelIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
  }
}

// ── Health Model ──

resource healthModel 'Microsoft.CloudHealth/healthModels@2026-01-01-preview' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${healthModelIdentity.id}': {}
    }
  }
  properties: {}
   // it's possible to create the Health Model before the role are assigned, but the moment it's created it will try to process signals
  dependsOn: [monitoringReaderRole, readerRole]
}

// ── Authentication Settings ──

resource authReader 'Microsoft.CloudHealth/healthModels/authenticationsettings@2026-01-01-preview' = {
  parent: healthModel
  name: 'auth-reader'
  properties: {
    authenticationKind: 'ManagedIdentity'
    displayName: 'HealthModel reader'
    managedIdentityName: healthModelIdentity.id
  }
}

// ══════════════════════════════════════════════════════════════════════
// SIGNAL DEFINITIONS — metric templates referenced by entity signal bindings
// ══════════════════════════════════════════════════════════════════════

// ── Search signals (always) ──

resource sdSearchLatency 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-search-latency'
  properties: {
    displayName: 'Search Query Latency'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Seconds'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.search/searchservices'
    metricName: 'SearchLatency'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 1 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 3 }
    }
  }
}

resource sdSearchQps 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-search-qps'
  properties: {
    displayName: 'Search Queries Per Second'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'CountPerSecond'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.search/searchservices'
    metricName: 'SearchQueriesPerSecond'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 50 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 100 }
    }
  }
}

resource sdSearchThrottle 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-search-throttle'
  properties: {
    displayName: 'Search Throttling'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Percent'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.search/searchservices'
    metricName: 'ThrottledSearchQueriesPercentage'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 25 }
    }
  }
}

resource sdSearchDocsProcessed 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-search-docs-processed'
  properties: {
    displayName: 'Documents Processed'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.search/searchservices'
    metricName: 'DocumentsProcessedCount'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 100000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 500000 }
    }
  }
}

resource sdSearchIndexSize 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-search-index-size'
  properties: {
    displayName: 'Search Index Storage'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Bytes'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.search/searchservices'
    metricName: 'IndexStorageUsage'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5368709120 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 10737418240 }
    }
  }
}

// ── Document Intelligence signals (always — unconditional resource) ──

resource sdDocIntelSuccessRate 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-docintel-success-rate'
  properties: {
    displayName: 'Doc Intelligence Success Rate'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Percent'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'SuccessRate'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'LessThan', threshold: 99 }
      unhealthyRule: { operator: 'LessThan', threshold: 95 }
    }
  }
}

resource sdDocIntelLatency 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-docintel-latency'
  properties: {
    displayName: 'Doc Intelligence Latency'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'MilliSeconds'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'Latency'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 10000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 30000 }
    }
  }
}

resource sdDocIntelErrors 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-docintel-errors'
  properties: {
    displayName: 'Doc Intelligence Errors'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'TotalErrors'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 50 }
    }
  }
}

resource sdDocIntelPages 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-docintel-pages'
  properties: {
    displayName: 'Doc Intelligence Pages Processed'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'ProcessedPages'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 10000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 50000 }
    }
  }
}

// ── Storage signals (always) ──

resource sdStorageTransactions 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-storage-transactions'
  properties: {
    displayName: 'Storage Transactions'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.storage/storageaccounts'
    metricName: 'Transactions'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 50000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 100000 }
    }
  }
}

resource sdStorageLatency 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = {
  parent: healthModel
  name: 'sd-storage-latency'
  properties: {
    displayName: 'Storage Server Latency'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'MilliSeconds'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.storage/storageaccounts'
    metricName: 'SuccessServerLatency'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 100 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 500 }
    }
  }
}

// ── Container Apps signals (conditional) ──

resource sdBackendCpu 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'sd-backend-cpu'
  properties: {
    displayName: 'Backend CPU Percentage'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Percent'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.app/containerapps'
    metricName: 'CpuPercentage'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 70 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 90 }
    }
  }
}

resource sdBackendMemory 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'sd-backend-memory'
  properties: {
    displayName: 'Backend Memory Percentage'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Percent'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.app/containerapps'
    metricName: 'MemoryPercentage'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 85 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 95 }
    }
  }
}

resource sdBackendRestarts 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'sd-backend-restarts'
  properties: {
    displayName: 'Backend Restarts'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.app/containerapps'
    metricName: 'RestartCount'
    aggregationType: 'Total'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 1 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 3 }
    }
  }
}

resource sdBackendRequests 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'sd-backend-requests'
  properties: {
    displayName: 'Backend Request Volume'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.app/containerapps'
    metricName: 'Requests'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 10000 }
    }
  }
}

resource sdAcaIngressCpu 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'sd-aca-ingress-cpu'
  properties: {
    displayName: 'ACA Ingress CPU'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Percent'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.app/managedenvironments'
    metricName: 'IngressCpuPercentage'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 70 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 90 }
    }
  }
}

// ── OpenAI signals (conditional) ──

resource sdOpenaiAvailability 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-availability'
  properties: {
    displayName: 'OpenAI Availability'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Percent'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'ModelAvailabilityRate'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'LessThan', threshold: 100 }
      unhealthyRule: { operator: 'LessThan', threshold: 95 }
    }
  }
}

resource sdOpenaiLatency 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-latency'
  properties: {
    displayName: 'OpenAI Response Latency'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'MilliSeconds'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'TimeToResponse'
    aggregationType: 'Average'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 3000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 8000 }
    }
  }
}

resource sdOpenaiThrottle 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-throttle'
  properties: {
    displayName: 'OpenAI Requests (Throttling)'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'ModelRequests'
    aggregationType: 'Total'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 500 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 1000 }
    }
  }
}

resource sdOpenaiTokens 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-tokens'
  properties: {
    displayName: 'OpenAI Token Burn Rate'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'TotalTokens'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 100000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 500000 }
    }
  }
}

resource sdOpenaiClientErrors 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-client-errors'
  properties: {
    displayName: 'OpenAI Client Errors (incl. context-too-long)'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'ClientErrors'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 50 }
    }
  }
}

resource sdOpenaiRatelimit 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-ratelimit'
  properties: {
    displayName: 'OpenAI Rate Limit Consumption'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT1M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'Ratelimit'
    aggregationType: 'Total'
    timeGrain: 'PT1M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 50000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 100000 }
    }
  }
}

resource sdOpenaiInputTokens 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-input-tokens'
  properties: {
    displayName: 'OpenAI Input (Prompt) Tokens'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'InputTokens'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 200000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 1000000 }
    }
  }
}

resource sdOpenaiOutputTokens 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-output-tokens'
  properties: {
    displayName: 'OpenAI Output (Completion) Tokens'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'OutputTokens'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 50000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 250000 }
    }
  }
}

resource sdOpenaiBlockedCalls 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'sd-openai-blocked-calls'
  properties: {
    displayName: 'OpenAI Content Policy Blocks'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.cognitiveservices/accounts'
    metricName: 'BlockedCalls'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 1 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 10 }
    }
  }
}

// ── Application Insights signals (conditional) ──

resource sdAppinsightsFailedRequests 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'sd-appinsights-failed-requests'
  properties: {
    displayName: 'Failed HTTP Requests'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.insights/components'
    metricName: 'requests/failed'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 50 }
    }
  }
}

resource sdAppinsightsExceptions 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'sd-appinsights-exceptions'
  properties: {
    displayName: 'Exceptions'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.insights/components'
    metricName: 'exceptions/count'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 1 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 10 }
    }
  }
}

resource sdAppinsightsResponseTime 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'sd-appinsights-response-time'
  properties: {
    displayName: 'HTTP Response Time'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'MilliSeconds'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.insights/components'
    metricName: 'requests/duration'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 15000 }
    }
  }
}

resource sdDependencyFailures 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'sd-dependency-failures'
  properties: {
    displayName: 'Dependency Call Failures'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.insights/components'
    metricName: 'dependencies/failed'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 3 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 20 }
    }
  }
}

resource sdDependencyDuration 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'sd-dependency-duration'
  properties: {
    displayName: 'Dependency Call Latency'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'MilliSeconds'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.insights/components'
    metricName: 'dependencies/duration'
    aggregationType: 'Average'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 5000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 15000 }
    }
  }
}

resource sdAppinsightsTraces 'Microsoft.CloudHealth/healthModels/signaldefinitions@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'sd-appinsights-traces'
  properties: {
    displayName: 'Telemetry Traces'
    signalKind: 'AzureResourceMetric'
    dataUnit: 'Count'
    refreshInterval: 'PT5M'
    metricNamespace: 'microsoft.insights/components'
    metricName: 'traces/count'
    aggregationType: 'Total'
    timeGrain: 'PT5M'
    evaluationRules: {
      degradedRule: { operator: 'GreaterThan', threshold: 500000 }
      unhealthyRule: { operator: 'GreaterThan', threshold: 1000000 }
    }
  }
}

// ══════════════════════════════════════════════════════════════════════
// ENTITIES — organized by use case, conditional on feature flags
// ══════════════════════════════════════════════════════════════════════

// ── Use-case group: RAG Chat (always) ──

resource entityRagChat 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = {
  parent: healthModel
  name: 'e-rag-chat'
  properties: {
    displayName: 'RAG Chat'
    impact: 'Standard'
    icon: { iconName: 'SystemComponent' }
    canvasPosition: {
      x: json('${xRagChat}')
      y: json('${canvasGroupRow}')
    }
  }
}

// Backend App — Container Apps variant
resource entityBackendComputeAca 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'e-backend-compute'
  properties: {
    displayName: 'Backend App'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xRagChat + 1 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: containerAppResourceId
        signals: [
          { name: 'sa-backend-requests', signalDefinitionName: sdBackendRequests.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-backend-restarts', signalDefinitionName: sdBackendRestarts.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-backend-cpu', signalDefinitionName: sdBackendCpu.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-backend-memory', signalDefinitionName: sdBackendMemory.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
        ]
      }
    }
  }
}

// Backend App — App Service variant
resource entityBackendComputeAppSvc 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (isAppService) {
  parent: healthModel
  name: 'e-backend-compute'
  properties: {
    displayName: 'Backend App'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: appServiceResourceId
        signals: []
      }
    }
  }
}
resource entityAiInference 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'e-ai-inference'
  properties: {
    displayName: 'AI Inference'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xRagChat + 3 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: cognitiveServicesResourceId
        signals: [
          { name: 'sa-openai-availability', signalDefinitionName: sdOpenaiAvailability.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-openai-latency', signalDefinitionName: sdOpenaiLatency.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-openai-throttle', signalDefinitionName: sdOpenaiThrottle.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-openai-tokens', signalDefinitionName: sdOpenaiTokens.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-openai-client-errors', signalDefinitionName: sdOpenaiClientErrors.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-openai-ratelimit', signalDefinitionName: sdOpenaiRatelimit.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-openai-input-tokens', signalDefinitionName: sdOpenaiInputTokens.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-openai-output-tokens', signalDefinitionName: sdOpenaiOutputTokens.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-openai-blocked-calls', signalDefinitionName: sdOpenaiBlockedCalls.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// Knowledge Search (always)
resource entityKnowledgeSearch 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = {
  parent: healthModel
  name: 'e-knowledge-search'
  properties: {
    displayName: 'Knowledge Search'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xRagChat + 0 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: searchServiceResourceId
        signals: [
          { name: 'sa-search-latency', signalDefinitionName: sdSearchLatency.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-search-qps', signalDefinitionName: sdSearchQps.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-search-throttle', signalDefinitionName: sdSearchThrottle.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT1M' }
          { name: 'sa-search-docs-processed', signalDefinitionName: sdSearchDocsProcessed.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-search-index-size', signalDefinitionName: sdSearchIndexSize.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// App Performance — application-level health signals bound to App Insights (under RAG Chat)
resource entityAppPerformance 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'e-app-performance'
  properties: {
    displayName: 'App Performance'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xRagChat + 2 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: applicationInsightsResourceId
        signals: [
          { name: 'sa-failed-requests', signalDefinitionName: sdAppinsightsFailedRequests.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-exceptions', signalDefinitionName: sdAppinsightsExceptions.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-response-time', signalDefinitionName: sdAppinsightsResponseTime.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-dependency-failures', signalDefinitionName: sdDependencyFailures.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-dependency-duration', signalDefinitionName: sdDependencyDuration.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// ── Use-case group: Document Ingestion (always) ──

resource entityDocIngestion 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = {
  parent: healthModel
  name: 'e-doc-ingestion'
  properties: {
    displayName: 'Document Ingestion'
    impact: 'Standard'
    icon: { iconName: 'SystemComponent' }
    canvasPosition: {
      x: json('${xDocIngestion}')
      y: json('${canvasGroupRow}')
    }
  }
}

// Document Storage (always)
resource entityDocStorage 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = {
  parent: healthModel
  name: 'e-doc-storage'
  properties: {
    displayName: 'Document Storage'
    impact: 'Standard'
    icon: { iconName: 'StorageAccount' }
    canvasPosition: {
      x: json('${xDocIngestion + 0 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: storageAccountResourceId
        signals: [
          { name: 'sa-storage-transactions', signalDefinitionName: sdStorageTransactions.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-storage-latency', signalDefinitionName: sdStorageLatency.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// Document Intelligence (always — Cognitive Services metrics for document parsing)
resource entityDocIntelligence 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = {
  parent: healthModel
  name: 'e-doc-intelligence'
  properties: {
    displayName: 'Document Intelligence'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xDocIngestion + 1 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: documentIntelligenceResourceId
        signals: [
          { name: 'sa-docintel-success-rate', signalDefinitionName: sdDocIntelSuccessRate.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-docintel-latency', signalDefinitionName: sdDocIntelLatency.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-docintel-errors', signalDefinitionName: sdDocIntelErrors.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
          { name: 'sa-docintel-pages', signalDefinitionName: sdDocIntelPages.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// ── Use-case group: Speech (conditional) ──

resource entitySpeech 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useSpeechOutputAzure) {
  parent: healthModel
  name: 'e-speech'
  properties: {
    displayName: 'Speech'
    impact: 'Standard'
    icon: { iconName: 'SystemComponent' }
    canvasPosition: {
      x: json('${xSpeech}')
      y: json('${canvasGroupRow}')
    }
  }
}

resource entitySpeechService 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useSpeechOutputAzure) {
  parent: healthModel
  name: 'e-speech-service'
  properties: {
    displayName: 'Speech Service'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xSpeech}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: speechServiceResourceId
        signals: []
      }
    }
  }
}

// ── Use-case group: Authentication & History (conditional) ──

resource entityAuthHistory 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useAuthenticationWithCosmos) {
  parent: healthModel
  name: 'e-auth-history'
  properties: {
    displayName: 'Authentication & History'
    impact: 'Standard'
    icon: { iconName: 'SystemComponent' }
    canvasPosition: {
      x: json('${xAuthHistory}')
      y: json('${canvasGroupRow}')
    }
  }
}

resource entityCosmosDb 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useAuthenticationWithCosmos) {
  parent: healthModel
  name: 'e-cosmos-db'
  properties: {
    displayName: 'Cosmos DB'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xAuthHistory}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: cosmosDbResourceId
        signals: []
      }
    }
  }
}

// ── Use-case group: Platform (conditional on containerapps) ──

resource entityPlatform 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'e-platform'
  properties: {
    displayName: 'Platform'
    impact: 'Standard'
    icon: { iconName: 'SystemComponent' }
    canvasPosition: {
      x: json('${xPlatform}')
      y: json('${canvasGroupRow}')
    }
  }
}

resource entityContainerPlatform 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'e-container-platform'
  properties: {
    displayName: 'Container Platform'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xPlatform}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: managedEnvironmentResourceId
        signals: [
          { name: 'sa-aca-ingress-cpu', signalDefinitionName: sdAcaIngressCpu.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// ── Use-case group: Observability (conditional on Application Insights) ──

resource entityObservability 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'e-observability'
  properties: {
    displayName: 'Observability'
    impact: 'Standard'
    icon: { iconName: 'SystemComponent' }
    canvasPosition: {
      x: json('${xObservability}')
      y: json('${canvasGroupRow}')
    }
  }
}

resource entityAppTelemetry 'Microsoft.CloudHealth/healthModels/entities@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'e-app-telemetry'
  properties: {
    displayName: 'Telemetry Pipeline'
    impact: 'Standard'
    icon: { iconName: 'Resource' }
    canvasPosition: {
      x: json('${xObservability + 0 * canvasLeafSpacing}')
      y: json('${canvasLeafRow}')
    }
    signalGroups: {
      azureResource: {
        authenticationSetting: authReader.name
        azureResourceId: applicationInsightsResourceId
        signals: [
          { name: 'sa-telemetry-traces', signalDefinitionName: sdAppinsightsTraces.name, signalKind: 'AzureResourceMetric', refreshInterval: 'PT5M' }
        ]
      }
    }
  }
}

// ══════════════════════════════════════════════════════════════════════
// RELATIONSHIPS — use-case hierarchy
// ══════════════════════════════════════════════════════════════════════

// Root → use-case groups
resource relRootRagChat 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = {
  parent: healthModel
  name: 'r-root-rag-chat'
  properties: {
    parentEntityName: healthModel.name
    childEntityName: entityRagChat.name
  }
}

resource relRootDocIngestion 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = {
  parent: healthModel
  name: 'r-root-doc-ingestion'
  properties: {
    parentEntityName: healthModel.name
    childEntityName: entityDocIngestion.name
  }
}

resource relRootSpeech 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useSpeechOutputAzure) {
  parent: healthModel
  name: 'r-root-speech'
  properties: {
    parentEntityName: healthModel.name
    childEntityName: entitySpeech.name
  }
}

resource relRootAuthHistory 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useAuthenticationWithCosmos) {
  parent: healthModel
  name: 'r-root-auth-history'
  properties: {
    parentEntityName: healthModel.name
    childEntityName: entityAuthHistory.name
  }
}

resource relRootPlatform 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'r-root-platform'
  properties: {
    parentEntityName: healthModel.name
    childEntityName: entityPlatform.name
  }
}

resource relRootObservability 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'r-root-observability'
  properties: {
    parentEntityName: healthModel.name
    childEntityName: entityObservability.name
  }
}

// RAG Chat children
resource relRagBackendAca 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'r-rag-chat-backend-compute'
  properties: {
    parentEntityName: entityRagChat.name
    childEntityName: entityBackendComputeAca.name
  }
}

resource relRagBackendAppSvc 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (isAppService) {
  parent: healthModel
  name: 'r-rag-chat-backend-compute'
  properties: {
    parentEntityName: entityRagChat.name
    childEntityName: entityBackendComputeAppSvc.name
  }
}

resource relRagAiInference 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (deployAzureOpenAi) {
  parent: healthModel
  name: 'r-rag-chat-ai-inference'
  properties: {
    parentEntityName: entityRagChat.name
    childEntityName: entityAiInference.name
  }
}

resource relRagKnowledgeSearch 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = {
  parent: healthModel
  name: 'r-rag-chat-knowledge-search'
  properties: {
    parentEntityName: entityRagChat.name
    childEntityName: entityKnowledgeSearch.name
  }
}

resource relRagAppPerformance 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'r-rag-chat-app-performance'
  properties: {
    parentEntityName: entityRagChat.name
    childEntityName: entityAppPerformance.name
  }
}

// Document Ingestion children
resource relDocIngestionStorage 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = {
  parent: healthModel
  name: 'r-doc-ingestion-storage'
  properties: {
    parentEntityName: entityDocIngestion.name
    childEntityName: entityDocStorage.name
  }
}

resource relDocIngestionIntelligence 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = {
  parent: healthModel
  name: 'r-doc-ingestion-intelligence'
  properties: {
    parentEntityName: entityDocIngestion.name
    childEntityName: entityDocIntelligence.name
  }
}

// Speech children
resource relSpeechService 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useSpeechOutputAzure) {
  parent: healthModel
  name: 'r-speech-service'
  properties: {
    parentEntityName: entitySpeech.name
    childEntityName: entitySpeechService.name
  }
}

// Auth & History children
resource relAuthCosmosDb 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useAuthenticationWithCosmos) {
  parent: healthModel
  name: 'r-auth-history-cosmos-db'
  properties: {
    parentEntityName: entityAuthHistory.name
    childEntityName: entityCosmosDb.name
  }
}

// Platform children
resource relPlatformContainer 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (isContainerApps) {
  parent: healthModel
  name: 'r-platform-container-platform'
  properties: {
    parentEntityName: entityPlatform.name
    childEntityName: entityContainerPlatform.name
  }
}

// Observability children
resource relObservabilityAppTelemetry 'Microsoft.CloudHealth/healthModels/relationships@2026-01-01-preview' = if (useApplicationInsights) {
  parent: healthModel
  name: 'r-observability-app-telemetry'
  properties: {
    parentEntityName: entityObservability.name
    childEntityName: entityAppTelemetry.name
  }
}

// ── Outputs ──

output healthModelName string = healthModel.name
output healthModelId string = healthModel.id
output identityPrincipalId string = healthModelIdentity.properties.principalId
output identityResourceId string = healthModelIdentity.id
