param identityName string
param location string

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

output principalId string = webIdentity.properties.principalId
output clientId string = webIdentity.properties.clientId
