param name string
param location string = resourceGroup().location
param tags object = {}

param database_name string = 'db_conversation_history'
param conversations_container_name string = 'conversations'

// deploy a cosmos db instance
resource cosmosdb 'Microsoft.DocumentDB/databaseAccounts@2022-11-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
    }
    isVirtualNetworkFilterEnabled: false
    virtualNetworkRules: []
    minimalTlsVersion: 'Tls12'
    capabilities: [
      {
        name: 'EnableServerless'
      }  
    ]
    capacity: {
      totalThroughputLimit: 1000
    }
    networkAclBypass: 'AzureServices'
    publicNetworkAccess: 'Enabled'
  }
}

// deploy the cosmosdb database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2022-11-15' = {
  parent: cosmosdb
  name: database_name
  properties: {
    resource: {
      id: database_name
    }
  }
}

// deploy the chatgpt conversation container
resource conversations_container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2022-11-15' = {
  parent: database
  name: conversations_container_name
  properties: {
    resource: {
      id: conversations_container_name
      partitionKey: {
        paths: [
          '/userId'
        ]
        kind: 'Hash'
      }
    }
  }
}
output cosmosdb object = cosmosdb
output id string = cosmosdb.id
output name string = cosmosdb.name
output endpoint string = cosmosdb.properties.documentEndpoint
output database_name string = database.name
output conversations_container_name string = conversations_container.name
