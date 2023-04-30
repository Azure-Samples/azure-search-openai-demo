param name string
param location string = resourceGroup().location
param tags object = {}

param cosmos_database_name string = 'db_conversation_history'
param cosmos_database_container_name string = 'chatgpt'

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
  name: cosmos_database_name
  properties: {
    resource: {
      id: cosmos_database_name
    }
  }
}

// deploy the chatgpt history container
resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2022-11-15' = {
  parent: database
  name: cosmos_database_container_name
  properties: {
    resource: {
      id: cosmos_database_container_name
      partitionKey: {
        paths: [
          '/userid'
        ]
        kind: 'Hash'
      }
    }
  }
}


output name string = cosmosdb.name
output endpoint string = cosmosdb.properties.documentEndpoint
output cosmosdb_database_name string = database.name
output cosmoddb_database_container_name string = container.name
