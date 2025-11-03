param appServiceName string

@description('The client ID of the Microsoft Entra application.')
param clientId string

param openIdIssuer string

resource appService 'Microsoft.Web/sites@2022-03-01' existing = {
  name: appServiceName
}

resource configAuth 'Microsoft.Web/sites/config@2022-03-01' = {
  parent: appService
  name: 'authsettingsV2'
  properties: {
    globalValidation: {
      requireAuthentication: true
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureactivedirectory'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: clientId
          clientSecretSettingName: 'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID'
          openIdIssuer: openIdIssuer
        }
        validation: {
          defaultAuthorizationPolicy: {
            allowedApplications: []
          }
        }
      }
    }
    login: {
      tokenStore: {
        enabled: true
      }
    }
  }
}
