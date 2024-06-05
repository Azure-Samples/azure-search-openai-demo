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
    computerVisionSkuName: 'S1'
    documentIntelligenceResourceGroupLocation: location
    documentIntelligenceSkuName: 'S0'
    openAiHost: 'azure'
    openAiResourceGroupLocation: location
    searchIndexName: 'gptkbindex'
    searchQueryLanguage: 'en-us'
    searchQuerySpeller: 'lexicon'
    searchServiceSemanticRankerLevel: 'free'
    searchServiceSkuName: 'standard'
    speechServiceSkuName: 'S0'
    storageSkuName: 'Standard_LRS'
    useApplicationInsights: false
    useVectors: true
    useGPT4V: false
    useSpeechInputBrowser: false
    useSpeechOutputBrowser: false

    // Test the secure configuration
    enableUnauthenticatedAccess: false
    usePrivateEndpoint: true
    publicNetworkAccess: 'Disabled'
  }
}
