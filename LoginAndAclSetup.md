# Setting up optional login and document level access control

## Table of Contents

- [Requirements](#requirements)
- [Setting up Azure AD Apps](#setting-up-azure-ad-apps)
  - [Server App](#server-app)
  - [Client App](#client-app)
- [Updating Frontend Code](#updating-frontend-code)
- [Setting Environment Variables](#setting-environment-variables)

This guide demonstrates how to add an optional login and document level access control system to the sample. This system can be used to restrict access to indexed data to specific users based on what [Azure Active Directory (Azure AD) groups](https://learn.microsoft.com/azure/active-directory/fundamentals/how-to-manage-groups) they are a part of, or their [user object id](https://learn.microsoft.com/partner-center/find-ids-and-domain-names#find-the-user-object-id).

![AppLoginArchitecture](./docs/applogincomponents.png)

## Requirements

**IMPORTANT:** In order to add optional login and document level access control, you'll need the following in addition to the normal sample requirements

* **Azure account permissions**: Your Azure account must have [permission to manage applications in Azure AD](https://learn.microsoft.com/azure/active-directory/develop/quickstart-register-app#prerequisites).


## Setting up Azure AD Apps

Two apps must be registered in order to make the optional login and document level access control system work correctly.

### Setting up the Server App

1. Sign in to the [Azure portal](https://portal.azure.com/).
1. Select the Azure AD Service.
1. In the left hand menu, select **Application Registrations**.
1. Select **New Registration**.
  1. In the **Name** section, enter a meaningful application name. This name will be displayed to users of the app, for example `Azure Search OpenAI Demo API`.
  1. Under **Supported account types**, select **Accounts in this organizational directory only**.
1. Select **Register** to create the application
1. In the app's registration screen, find the **Application (client) ID**.
  1. Run the following `azd` command to save this ID: `azd env set AZURE_SERVER_APP_ID <Application (client) ID>`.
1. Select **Certificates & secrets** in the left hand menu.
1. In the **Client secrets** section, select **New client secret**.
  1. Type a description, for example `Azure Search OpenAI Demo Key`.
  1. Select one of the available key durations.
  1. The generated key value will be displayed after you select **Add**.
  1. Copy the generated ke value and run the following `azd` command to save this ID: `azd env set AZURE_SERVER_APP_SECRET <generated key value>`.
1. Select **API Permissions** in the left hand menu. By default, the [delegated `User.Read`](https://learn.microsoft.com/graph/permissions-reference#user-permissions) permission should be present. This permission is required to read the signed-in user's profile to get the security information used for document level access control. If this permission is not present, it needs to be added to the application.
  1. Select **Add a permission**, and then **Microsoft Graph**.
  1. Select **Delegated permissions**.
  1. Search for and and select `User.Read`.
  1. Select **Add permissions**.
1. Select **Expose an API** in the left hand menu. The server app works by using the [https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow#protocol-diagram](On-Behalf-Of Flow), which requires the server app to expose at least 1 API.
  1. The application must define a URI to expose APIs. Select **Add** next to **Application ID URI**.
  1. By default, the Application ID URI is set to `api://<application client id>`. Accept the default by selecting **Save**.
  1. Under **Scopes defined by this API**, select **Add a scope**.
  1. Fill in the values as indicated:
    1. For **Scope name**, use **access_as_user**.
    1. For **Who can consent?**, select **Admins and users**.
    1. For **Admin consent display name**, type **Access Azure Search OpenAI Demo API**.
    1. For **Admin consent description**, type **Allows the app to access Azure Search OpenAI Demo API as the signed-in user.**.
    1. For **User consent display name**, type **Access Azure Search OpenAI Demo API**.
    1. For **User consent description**, type **Allow the app to access Azure Search OpenAI Demo API on your behalf**.
    1. Leave **State** set to **Enabled**.
    1. Select **Add scope** at the bottom to save the scope.

### Client App

1. Sign in to the [Azure portal](https://portal.azure.com/).
1. Select the Azure AD Service.
1. In the left hand menu, select **Application Registrations**.
1. Select **New Registration**.
  1. In the **Name** section, enter a meaningful application name. This name will be displayed to users of the app, for example `Azure Search OpenAI Demo Web App`.
  1. Under **Supported account types**, select **Accounts in this organizational directory only**.
  1. Under `Redirect URI (optional)` section, select `Single-page application (SPA)` in the combo-box and enter the following redirect URI:
    1. If you are running the sample locally, use `http://localhost:50505/redirect`.
    1. If you are running the sample, use the endpoint provided by `azd up`: `https://<your-endpoint>.azurewebsites.net/redirect`.
1. Select **Register** to create the application
1. In the app's registration screen, find the **Application (client) ID**.
  1. Run the following `azd` command to save this ID: `azd env set AZURE_CLIENT_APP_ID <Application (client) ID>`.
1. In the left hand menu, select **API permissions**. You will add permission to access the **access_as_user** API on the server app. This permission is required for the [https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow#protocol-diagram](On-Behalf-Of Flow) to work.
  1. Select **Add a permission**, and then **My APIs**.
  1. In the list of applications, select your server application **Azure Search OpenAI Demo API**
  1. Ensure **Delegated permissions** is selected.
  1. In the **Select permissions** section, select the **access_as_user** permission
  1. Select **Add permissions**.

### Configure Server App Manifest

Consent from the user must be obtained for use of the client and server app. The client app can prompt the user for consent through a dialog when they log in. The server app has no ability to show a dialog for consent. The [known client applications list](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow#gaining-consent-for-the-middle-tier-application) can be used to request consent for both the server app and the client app in the client app's dialog.

1. Navigate to the server app registration
1. In the left hand menu, select **Manifest**
1. In the manifest editor, replace `"knownClientApplications": []` with `"knownClientApplications": ["<client application id>"]`
1. Select **Save** to save your changes to the manifest

## Updating Frontend Code

1. Open the `app/frontend/src/authConfig.ts` file using a code editor.
1. 

## Setting Environment Variables