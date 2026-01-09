// This file is for doing static analysis and contains sensible defaults
// for PSRule to minimise false-positives and provide the best results.

// This file is not intended to be used as a runtime configuration file.

targetScope = 'subscription'

param environmentName string = 'testing'
param location string = 'swedencentral'

module main 'main.bicep' = {
  name: 'main'
  params: {
    environmentName: environmentName
    location: location
    appServiceSkuName: 'B1'
    azureContainerAppsWorkloadProfile: 'Consumption'
    cosmosDbSkuName: 'serverless'
    defaultReasoningEffort: 'medium'
    documentIntelligenceResourceGroupLocation: location
    documentIntelligenceSkuName: 'S0'
    openAiHost: 'azure'
    openAiLocation: location
    searchFieldNameEmbedding: 'embedding'
    searchIndexName: 'gptkbindex'
    searchQueryLanguage: 'en-us'
    searchQuerySpeller: 'lexicon'
    searchServiceQueryRewriting: 'none'
    searchServiceSemanticRankerLevel: 'free'
    searchServiceSkuName: 'standard'
    speechServiceSkuName: 'S0'
    storageSkuName: 'Standard_LRS'
    useAgenticKnowledgeBase: false
    useApplicationInsights: false
    useVectors: true
    useMultimodal: true
    enableLanguagePicker: false
    useSpeechInputBrowser: false
    useSpeechOutputBrowser: false
    webAppExists: false

    // Test the secure configuration
    enableUnauthenticatedAccess: false
    usePrivateEndpoint: true
    publicNetworkAccess: 'Disabled'
  }
}
