extension microsoftGraphV1

@description('Specifies the name of cloud environment to run this deployment in.')
param cloudEnvironment string = environment().name

@description('The unique name for the application registration (used for idempotency)')
param appUniqueName string

// NOTE: Microsoft Graph Bicep file deployment is only supported in Public Cloud
@description('Audience uris for public and national clouds')
param audiences object = {
  AzureCloud: {
    uri: 'api://AzureADTokenExchange'
  }
  AzureUSGovernment: {
    uri: 'api://AzureADTokenExchangeUSGov'
  }
  USNat: {
    uri: 'api://AzureADTokenExchangeUSNat'
  }
  USSec: {
    uri: 'api://AzureADTokenExchangeUSSec'
  }
  AzureChinaCloud: {
    uri: 'api://AzureADTokenExchangeChina'
  }
}

@description('Specifies the ID of the user-assigned managed identity.')
param webAppIdentityId string

@description('Specifies the unique name for the client application.')
param clientAppName string

@description('Specifies the display name for the client application')
param clientAppDisplayName string

param serviceManagementReference string = ''

param issuer string

param webAppEndpoint string

// Combine default scope with custom scopes
var defaultScopeValue = 'user_impersonation'
var defaultScopeId = guid(appUniqueName, 'default-scope', defaultScopeValue)

var userImpersonationScope = {
    adminConsentDescription: 'Allow the application to access the API on behalf of the signed-in user'
    adminConsentDisplayName: 'Access application as user'
    id: defaultScopeId
    isEnabled: true
    type: 'User'
    userConsentDescription: 'Allow the application to access the API on behalf of the signed-in user'
    userConsentDisplayName: 'Access application as user'
    value: defaultScopeValue
}

var allScopes = [
  userImpersonationScope
]

// Is this going to work with search service? Otherwise we have to set behind the scene?
var identifierUri = 'api://${appUniqueName}-${uniqueString(subscription().id, resourceGroup().id, appUniqueName)}'

resource appRegistration 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: clientAppName
  displayName: clientAppDisplayName
  signInAudience: 'AzureADMyOrg'
  serviceManagementReference: empty(serviceManagementReference) ? null : serviceManagementReference
  identifierUris: [identifierUri]
  api: {
    oauth2PermissionScopes: allScopes
    requestedAccessTokenVersion: 2
    // Not doing preauthorized apps
  }
  web: {
    redirectUris: [
      '${webAppEndpoint}/.auth/login/aad/callback'
    ]
    implicitGrantSettings: { enableIdTokenIssuance: true }
  }
  requiredResourceAccess: [
  {
      // Microsoft Graph permissions
      resourceAppId: '00000003-0000-0000-c000-000000000000'
      resourceAccess: [
        {
          // User.Read delegated permission
          id: 'e1fe6dd8-ba31-4d61-89e7-88639da4683d'
          type: 'Scope'
        }
      ]
    }
  ]

}

resource appServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: appRegistration.appId
}

resource federatedIdentityCredential 'Microsoft.Graph/applications/federatedIdentityCredentials@v1.0' = {
  name: '${appRegistration.uniqueName}/miAsFic'
  audiences: [
    audiences[cloudEnvironment].uri
  ]
  issuer: issuer
  subject: webAppIdentityId
}

output clientAppId string = appRegistration.appId
output clientSpId string = appServicePrincipal.id

@description('The identifier URI of the application - returns the actual URI that was set')
output identifierUri string = identifierUri
