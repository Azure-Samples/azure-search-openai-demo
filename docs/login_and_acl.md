<!--
---
name: RAG chat with document security
description: This guide demonstrates how to add an optional login and document level access control system to a RAG chat app for your domain data. This system can be used to restrict access to indexed data to specific users.
languages:
- python
- typescript
- bicep
- azdeveloper
products:
- azure-openai
- azure-cognitive-search
- azure-app-service
- azure
page_type: sample
urlFragment: azure-search-openai-demo-document-security
---
-->

# RAG chat: Setting up optional login and document level access control

[📺 Watch: (RAG Deep Dive series) Login and access control](https://www.youtube.com/watch?v=GwEiYJgM8Vw)

The [azure-search-openai-demo](/) project can set up a full RAG chat app on Azure AI Search and OpenAI so that you can chat on custom data, like internal enterprise data or domain-specific knowledge sets. For full instructions on setting up the project, consult the [main README](/README.md), and then return here for detailed instructions on configuring login and access control.

## Table of Contents

- [Requirements](#requirements)
- [Setting up Microsoft Entra applications](#setting-up-microsoft-entra-applications)
  - [Automatic Setup](#automatic-setup)
  - [Manual Setup](#manual-setup)
    - [Server App](#server-app)
    - [Client App](#client-app)
    - [Configure Server App Known Client Applications](#configure-server-app-known-client-applications)
    - [Testing](#testing)
    - [Programmatic Access With Authentication](#programmatic-access-with-authentication)
  - [Troubleshooting](#troubleshooting)
- [Adding data with document level access control](#adding-data-with-document-level-access-control)
  - [Using the Add Documents API](#using-the-add-documents-api)
    - [Enabling global access on documents without access control](#enabling-global-access-on-documents-without-access-control)
  - [Azure Data Lake Storage Gen2 and prepdocs](#azure-data-lake-storage-gen2-setup)
- [Migrate to built-in document access control](#migrate-to-built-in-document-access-control)
- [Environment variables reference](#environment-variables-reference)
  - [Authentication behavior by environment](#authentication-behavior-by-environment)

This guide demonstrates how to add an optional login and document level access control system to the sample. This system can be used to restrict access to indexed data to specific users based on what [Microsoft Entra groups](https://learn.microsoft.com/entra/fundamentals/how-to-manage-groups) they are a part of, or their [user object id](https://learn.microsoft.com/partner-center/find-ids-and-domain-names#find-the-user-object-id). This system utilizes the [built-in document access and control from Azure AI Search](https://learn.microsoft.com/azure/search/search-query-access-control-rbac-enforcement).

![AppLoginArchitecture](/docs/images/applogincomponents.png)

## Requirements

**IMPORTANT:** In order to add optional login and document level access control, you'll need the following in addition to the normal sample requirements

- **Azure account permissions**: Your Azure account must have [permission to manage applications in Microsoft Entra](https://learn.microsoft.com/entra/identity/role-based-access-control/permissions-reference#cloud-application-administrator).

## Setting up Microsoft Entra applications

Two Microsoft Entra applications must be registered in order to make the optional login and document level access control system work correctly. One app is for the client UI. The client UI is implemented as a [single page application](https://learn.microsoft.com/entra/identity-platform/scenario-spa-app-registration). The other app is for the API server. The API server uses a [confidential client](https://learn.microsoft.com/entra/identity-platform/msal-client-applications) to call the [Microsoft Graph API](https://learn.microsoft.com/graph/use-the-api).

### Automatic Setup

The easiest way to setup the two apps is to use the `azd` CLI. We've written scripts that will automatically create the two apps and configure them for use with the sample. To trigger the automatic setup, run the following commands:

1. **Enable authentication for the app**
  Run the following command to show the login UI and use Entra authentication by default:

    ```shell
    azd env set AZURE_USE_AUTHENTICATION true
    ```

1. (Optional) **Enforce access control**
  To ensure that the app restricts search results to only documents that the user has access to, run the following command:

    ```shell
    azd env set AZURE_ENFORCE_ACCESS_CONTROL true
    ```

1. (Optional) **Allow global document access**
  To allow upload of documents that have global access when there are no document-specific access controls assigned, run the following command:

    ```shell
    azd env set AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS true
    ```

1. (Optional) **Allow unauthenticated access**
  To allow unauthenticated users to use the app, run the following command:

    ```shell
    azd env set AZURE_ENABLE_UNAUTHENTICATED_ACCESS true
    ```

    Note: These users will not be able to search on documents that have access control assigned, so `AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS` should also be set to true to give them access to the remaining documents.

1. **Set the authentication tenant ID**
  Specify the tenant ID associated with authentication by running:

    ```shell
    azd env set AZURE_AUTH_TENANT_ID <YOUR-TENANT-ID>
    ```

1. **Login to the authentication tenant (if needed)**
  If your auth tenant ID is different from your currently logged in tenant ID, run:

    ```shell
    azd auth login --tenant-id <YOUR-TENANT-ID>
    ```

1. **Enable access control on your search index (if it already exists)**

    If your search index already exists, you need to enable access control on it:

    ```shell
    python ./scripts/manageacl.py --acl-action enable_acls
    ```

    If your index does not exist yet, access control will be automatically enabled when the index is created during deployment.

1. **Deploy the app**
  Finally, run the following command to provision and deploy the app:

    ```shell
    azd up
    ```

### Manual Setup

The following instructions explain how to setup the two apps using the Azure Portal.

#### Server App

- Sign in to the [Azure portal](https://portal.azure.com/).
- Select the Microsoft Entra ID service.
- In the left hand menu, select **Application Registrations**.
- Select **New Registration**.
  - In the **Name** section, enter a meaningful application name. This name will be displayed to users of the app, for example `Azure Search OpenAI Chat API`.
  - Under **Supported account types**, select **Accounts in this organizational directory only**.
- Select **Register** to create the application
- In the app's registration screen, find the **Application (client) ID**.
  - Run the following `azd` command to save this ID: `azd env set AZURE_SERVER_APP_ID <Application (client) ID>`.

- Microsoft Entra supports three types of credentials to authenticate an app using the [client credentials](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-client-creds-grant-flow): passwords (app secrets), certificates, and federated identity credentials. For a higher level of security, either [certificates](https://learn.microsoft.com/entra/identity-platform/howto-create-self-signed-certificate) or federated identity credentials are recommended. This sample currently uses an app secret for ease of provisioning.

- Select **Certificates & secrets** in the left hand menu.
- In the **Client secrets** section, select **New client secret**.
  - Type a description, for example `Azure Search OpenAI Chat Key`.
  - Select one of the available key durations.
  - The generated key value will be displayed after you select **Add**.
  - Copy the generated key value and run the following `azd` command to save this ID: `azd env set AZURE_SERVER_APP_SECRET <generated key value>`.
- Select **API Permissions** in the left hand menu. By default, the [delegated `User.Read`](https://learn.microsoft.com/graph/permissions-reference#user-permissions) permission should be present. This permission is required to read the signed-in user's profile.
  - Select **Add a permission**, and then **Microsoft Graph**.
  - Select **Delegated permissions**.
  - Search for and and select `User.Read`.
  - Select **Add permissions**.
- Select **API Permissions** in the left hand menu. The server app will use the `user_impersonation` permission from Azure AI Search to issue a token for security filtering on behalf of the logged in user.
  - Select **Add a permission**, and then **APIs my organization uses**.
  - Search for and select **Azure Cognitive Search**.
  - Select **Delegated permissions**.
  - Search for and and select `user_impersonation`.
  - Select **Add permissions**.
- Select **Expose an API** in the left hand menu. The server app works by using the [On Behalf Of Flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow#protocol-diagram), which requires the server app to expose at least 1 API.
  - The application must define a URI to expose APIs. Select **Add** next to **Application ID URI**.
    - By default, the Application ID URI is set to `api://<application client id>`. Accept the default by selecting **Save**.
  - Under **Scopes defined by this API**, select **Add a scope**.
  - Fill in the values as indicated:
    - For **Scope name**, use **access_as_user**.
    - For **Who can consent?**, select **Admins and users**.
    - For **Admin consent display name**, type **Access Azure Search OpenAI Chat API**.
    - For **Admin consent description**, type **Allows the app to access Azure Search OpenAI Chat API as the signed-in user.**.
    - For **User consent display name**, type **Access Azure Search OpenAI Chat API**.
    - For **User consent description**, type **Allow the app to access Azure Search OpenAI Chat API on your behalf**.
    - Leave **State** set to **Enabled**.
    - Select **Add scope** at the bottom to save the scope.

#### Client App

- Sign in to the [Azure portal](https://portal.azure.com/).
- Select the Microsoft Entra ID service.
- In the left hand menu, select **Application Registrations**.
- Select **New Registration**.
  - In the **Name** section, enter a meaningful application name. This name will be displayed to users of the app, for example `Azure Search OpenAI Chat Web App`.
  - Under **Supported account types**, select **Accounts in this organizational directory only**.
  - Under `Redirect URI (optional)` section, select `Single-page application (SPA)` in the combo-box and enter the following redirect URI:
    - If you are running the sample locally, add the endpoints `http://localhost:50505/redirect` and `http://localhost:5173/redirect`
    - If you are running the sample on Azure, add the endpoints provided by `azd up`: `https://<your-endpoint>.azurewebsites.net/redirect`.
    - If you are running the sample from Github Codespaces, add the Codespaces endpoint: `https://<your-codespace>-50505.app.github.dev/redirect`
- Select **Register** to create the application
- In the app's registration screen, find the **Application (client) ID**.
  - Run the following `azd` command to save this ID: `azd env set AZURE_CLIENT_APP_ID <Application (client) ID>`.
- In the left hand menu, select **Authentication**.
  - Under Web, add a redirect URI with the endpoint provided by `azd up`: `https://<your-endpoint>.azurewebsites.net/.auth/login/aad/callback`.
  - Under **Implicit grant and hybrid flows**, select **ID Tokens (used for implicit and hybrid flows)**
  - Select **Save**
- In the left hand menu, select **API permissions**. You will add permission to access the **access_as_user** API on the server app. This permission is required for the [On Behalf Of Flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow#protocol-diagram) to work.
  - Select **Add a permission**, and then **My APIs**.
  - In the list of applications, select your server application **Azure Search OpenAI Chat API**
  - Ensure **Delegated permissions** is selected.
  - In the **Select permissions** section, select the **access_as_user** permission
  - Select **Add permissions**.
- Stay in the **API permissions** section and select **Add a permission**.
  - Select **Microsoft Graph**.
  - Select **Delegated permissions**.
  - Search for and select `User.Read`.
  - Select **Add permissions**.

#### Configure Server App Known Client Applications

Consent from the user must be obtained for use of the client and server app. The client app can prompt the user for consent through a dialog when they log in. The server app has no ability to show a dialog for consent. Client apps can be [added to the list of known clients](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow#gaining-consent-for-the-middle-tier-application) to access the server app, so a consent dialog is shown for the server app.

- Navigate to the server app registration
- In the left hand menu, select **Manifest**
- Replace `"knownClientApplications": []` with `"knownClientApplications": ["<client application id>"]`
- Select **Save**

#### Testing

If you are running setup for the first time, ensure you have run `azd env set AZURE_ADLS_GEN2_STORAGE_ACCOUNT <YOUR-STORAGE_ACCOUNT>` before running `azd up`. If you do not set this environment variable, your index will not be initialized with access control support when `prepdocs` is run for the first time. To manually enable access control in your index, use the [manual setup script](#azure-data-lake-storage-gen2-setup).

Ensure you run `azd env set AZURE_USE_AUTHENTICATION` to enable the login UI once you have setup the two Microsoft Entra apps before you deploy or run the application. The login UI will not appear unless all [required environment variables](#environment-variables-reference) have been setup.

#### Programmatic Access with Authentication

If you want to use the chat endpoint without the UI and still use authentication, you must disable [App Service built-in authentication](https://learn.microsoft.com/azure/app-service/overview-authentication-authorization) and use only the app's MSAL-based authentication flow. Ensure the `AZURE_DISABLE_APP_SERVICES_AUTHENTICATION` environment variable is set before deploying.

Get an access token that can be used for calling the chat API using the following code:

```python
from azure.identity import DefaultAzureCredential
import os

token = DefaultAzureCredential().get_token(f"api://{os.environ['AZURE_SERVER_APP_ID']}/access_as_user", tenant_id=os.getenv('AZURE_AUTH_TENANT_ID', os.getenv('AZURE_TENANT_ID')))

print(token.token)
```

### Troubleshooting

- If your primary tenant restricts the ability to create Entra applications, you'll need to use a separate tenant to create the Entra applications. You can create a new tenant by following [these instructions](https://learn.microsoft.com/entra/identity-platform/quickstart-create-new-tenant). Then run `azd env set AZURE_AUTH_TENANT_ID <YOUR-AUTH-TENANT-ID>` before running `azd up`.
- If any Entra apps need to be recreated, you can avoid redeploying the app by [changing the app settings in the portal](https://learn.microsoft.com/azure/app-service/configure-common?tabs=portal#configure-app-settings). Any of the [required environment variables](#environment-variables-reference) can be changed. Once the environment variables have been changed, restart the web app.
- It's possible a consent dialog will not appear when you log into the app for the first time. If this consent dialog doesn't appear, you will be unable to use the security filters because the API server app does not have permission to read your authorization information. A consent dialog can be forced to appear by adding `"prompt": "consent"` to the `loginRequest` property in [`authentication.py`](/app/backend/core/authentication.py)
- It's possible that your tenant admin has placed a restriction on consent to apps with [unverified publishers](https://learn.microsoft.com/entra/identity-platform/publisher-verification-overview). In this case, only admins may consent to the client and server apps, and normal user accounts are unable to use the login system until the admin consents on behalf of the entire organization.
- It's possible that your tenant admin requires [admin approval of all new apps](https://learn.microsoft.com/entra/identity/enterprise-apps/manage-consent-requests). Regardless of whether you select the delegated or admin permissions, the app will not work without tenant admin consent. See this guide for [granting consent to an app](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent?pivots=portal).

## Adding data with document level access control

The sample supports 2 main strategies for adding data with document level access control.

- [Using the Add Documents API](#using-the-add-documents-api). Sample scripts are provided which use the Azure AI Search Service Add Documents API to directly manage access control information on _existing documents_ in the index.
- [Using prepdocs and Azure Data Lake Storage Gen 2](#azure-data-lake-storage-gen2-setup). Sample scripts are provided which set up an [Azure Data Lake Storage Gen 2](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction) account, set the [access control information](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control) on files and folders stored there, and ingest those documents into the search index with their  access control information.

### Using the Add Documents API

Manually enable document level access control on a search index and manually set access control values using the [manageacl.py](/scripts/manageacl.py) script.

Prior to running the script:

- Run `azd up` or use `azd env set` to manually set the `AZURE_SEARCH_SERVICE` and `AZURE_SEARCH_INDEX` azd environment variables
- Activate the Python virtual environment for your shell session

The script supports the following commands. All commands support `-v` for verbose logging.

- `python ./scripts/manageacl.py --acl-action enable_acls`: Creates the required `oids` (User ID) and `groups` (Group IDs) [security filter](https://learn.microsoft.com/azure/search/search-security-trimming-for-azure-search) fields for document level access control on your index, as well as the `storageUrl` field for storing the Blob storage URL. Does nothing if these fields already exist.

  Example usage:

  ```shell
  python ./scripts/manageacl.py -v --acl-action enable_acls
  ```

- `python ./scripts/manageacl.py --acl-type [oids or groups]--acl-action view --url [https://url.pdf]`: Prints access control values associated with either User IDs or Group IDs for the document at the specified URL.

  Example to view all Group IDs:

  ```shell
  python ./scripts/manageacl.py -v --acl-type groups --acl-action view --url https://st12345.blob.core.windows.net/content/Benefit_Options.pdf
  ```

- `python ./scripts/manageacl.py --acl-type [oids or groups] --acl-action add --acl [ID of group or user] --url [https://url.pdf]`: Adds an access control value associated with either User IDs or Group IDs for the document at the specified URL.

  Example to add a Group ID:

  ```shell
  python ./scripts/manageacl.py -v --acl-type groups --acl-action add --acl xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --url https://st12345.blob.core.windows.net/content/Benefit_Options.pdf
  ```

- `python ./scripts/manageacl.py --acl-type [oids or groups]--acl-action remove_all --url [https://url.pdf]`: Removes all access control values associated with either User IDs or Group IDs for a specific document.

  Example to remove all Group IDs:

  ```shell
  python ./scripts/manageacl.py -v --acl-type groups --acl-action remove_all --url https://st12345.blob.core.windows.net/content/Benefit_Options.pdf
  ```

- `python ./scripts/manageacl.py --url [https://url.pdf] --acl-type [oids or groups]--acl-action remove --acl [ID of group or user]`: Removes an access control value associated with either User IDs or Group IDs for a specific document.

  Example to remove a specific User ID:

  ```shell
  python ./scripts/manageacl.py -v --acl-type oids --acl-action remove --acl xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --url https://st12345.blob.core.windows.net/content/Benefit_Options.pdf
  ```

#### Enabling global access on documents without access control

- `python ./scripts/manageacl.py --acl-action enable_global_access`: Set the special [`["all"]`](https://learn.microsoft.com/azure/search/search-index-access-control-lists-and-rbac-push-api#special-acl-values-all-and-none) on the `oids` (User ID) and `groups` (Group IDs) security filter fields in your index on documents that do not have any existing `oids` or `groups` access control. This will enable any signed-in user to query these documents.

### Azure Data Lake Storage Gen2 Setup

[Azure Data Lake Storage Gen2](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction) implements an [access control model](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control) that can be used for document level access control. The [adlsgen2setup.py](/scripts/adlsgen2setup.py) script uploads the sample data included in the [data](./data) folder to a Data Lake Storage Gen2 storage account. The [Storage Blob Data Owner](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control-model#role-based-access-control-azure-rbac) role is required to use the script.

In order to use this script, an existing Data Lake Storage Gen2 storage account is required. Run `azd env set AZURE_ADLS_GEN2_STORAGE_ACCOUNT <your-storage-account>` prior to running the script.

Then run the script inside your Python environment:

```shell
python /scripts/adlsgen2setup.py './data/*' --data-access-control './scripts/sampleacls.json' -v
```

The script performs the following steps:

- Creates example [groups](https://learn.microsoft.com/entra/fundamentals/how-to-manage-groups) listed in the [sampleacls.json](/scripts/sampleacls.json) file.
- Creates a filesystem / container `gptkbcontainer` in the storage account.
- Creates the directories listed in the [sampleacls.json](/scripts/sampleacls.json) file.
- Uploads the sample PDFs referenced in the [sampleacls.json](/scripts/sampleacls.json) file into the appropriate directories.
- [Recursively sets Access Control Lists (ACLs)](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-acl-cli) using the information from the [sampleacls.json](/scripts/sampleacls.json) file.

In order to use the sample access control, you need to join these groups in your Microsoft Entra tenant.

Note that this optional script may not work in Codespaces if your administrator has applied a [Conditional Access policy](https://learn.microsoft.com/entra/identity/conditional-access/overview) to your tenant.

#### Azure Data Lake Storage Gen2 Prep Docs

Once a Data Lake Storage Gen2 storage account has been setup with sample data and access control lists, [prepdocs.py](/app/backend/prepdocs.py) can be used to automatically process PDFs in the storage account and store them with their [access control lists in the search index](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control).

To run this script with a Data Lake Storage Gen2 account, first set the following environment variables:

- `AZURE_ADLS_GEN2_STORAGE_ACCOUNT`: Name of existing [Data Lake Storage Gen2 storage account](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction).
- (Optional) `AZURE_ADLS_GEN2_FILESYSTEM`: Name of existing Data Lake Storage Gen2 filesystem / container in the storage account. If empty, `gptkbcontainer` is used.
- (Optional) `AZURE_ADLS_GEN2_FILESYSTEM_PATH`: Specific path in the Data Lake Storage Gen2 filesystem / container to process. Only PDFs contained in this path will be processed.

Once the environment variables are set, run the script using the following command: `/scripts/prepdocs.ps1` or `/scripts/prepdocs.sh`.

## Migrate to built-in document access control

Previous versions of the sample used [security filters](https://learn.microsoft.com/azure/search/search-security-trimming-for-azure-search) to implement document-level access control.
To support [built-in access control](https://learn.microsoft.com/azure/search/search-query-access-control-rbac-enforcement), deployment takes the following steps:

1. Adds the `user_impersonation` permission for Azure AI Search to the server app
2. Enables [permission filtering](https://learn.microsoft.com/azure/search/search-index-access-control-lists-and-rbac-push-api#create-an-index-with-permission-filter-fields) on the existing index.
3. Sets the [x-ms-query-source-authorization](https://learn.microsoft.com/azure/search/search-query-access-control-rbac-enforcement#how-query-time-enforcement-works) header on every query when `AZURE_ENFORCE_ACCESS_CONTROL` is enabled.

When `AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS` was enabled, previous versions of the sample interpreted no access control on a document as meaning that the document was globally available. Built-in document access control requires [`["all"]`](https://learn.microsoft.com/azure/search/search-index-access-control-lists-and-rbac-push-api#special-acl-values-all-and-none) to be set for each globally available document. You can run a [one-time migration](#enabling-global-access-on-documents-without-access-control) on your existing index to enable global access for these documents.

## Environment variables reference

The following environment variables are used to setup the optional login and document level access control:

- `AZURE_USE_AUTHENTICATION`: Enables Entra ID login and document level access control. Set to true before running `azd up`.
- `AZURE_ENFORCE_ACCESS_CONTROL`: Enforces Entra ID based login and document level access control on documents with access control assigned. Set to true before running `azd up`. If `AZURE_ENFORCE_ACCESS_CONTROL` is enabled and `AZURE_ENABLE_UNAUTHENTICATED_ACCESS` is not enabled, then authentication is required to use the app.
- `AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS`: Enables prepdocs upload code to support setting user ids and group ids to `["all"]` when uploading documents that have no access control assigned. This will enable the built-in document level access control to return these documents if `AZURE_ENFORCE_ACCESS_CONTROL` is enabled. If you are migrating from a previous version where this was not required, you'll have to perform a [one-time migration](#migrate-to-built-in-document-access-control) to enable global document access.
- `AZURE_ENABLE_UNAUTHENTICATED_ACCESS`: Allows unauthenticated users to access the chat app. If `AZURE_ENFORCE_ACCESS_CONTROL` is enabled, unauthenticated users cannot search on documents.
- `AZURE_DISABLE_APP_SERVICES_AUTHENTICATION`: Disables [use of built-in authentication for App Services](https://learn.microsoft.com/azure/app-service/overview-authentication-authorization). An authentication flow based on the MSAL SDKs is used instead. Useful when you want to provide programmatic access to the chat endpoints with authentication.
- `AZURE_SERVER_APP_ID`: (Required) Application ID of the Microsoft Entra app for the API server.
- `AZURE_SERVER_APP_SECRET`: [Client secret](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-client-creds-grant-flow) used by the API server to authenticate using the Microsoft Entra server app.
- `AZURE_CLIENT_APP_ID`: Application ID of the Microsoft Entra app for the client UI.
- `AZURE_AUTH_TENANT_ID`: [Tenant ID](https://learn.microsoft.com/entra/fundamentals/how-to-find-tenant) associated with the Microsoft Entra tenant used for login and document level access control. Defaults to `AZURE_TENANT_ID` if not defined.
- `AZURE_ADLS_GEN2_STORAGE_ACCOUNT`: (Optional) Name of existing [Data Lake Storage Gen2 storage account](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction) for storing sample data with [access control lists](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control). Only used with the optional Data Lake Storage Gen2 [setup](#azure-data-lake-storage-gen2-setup) and [prep docs](#azure-data-lake-storage-gen2-prep-docs) scripts.
- `AZURE_ADLS_GEN2_FILESYSTEM`: (Optional) Name of existing [Data Lake Storage Gen2 filesystem](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction) for storing sample data with [access control lists](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control). Only used with the optional Data Lake Storage Gen2 [setup](#azure-data-lake-storage-gen2-setup) and [prep docs](#azure-data-lake-storage-gen2-prep-docs) scripts.
- `AZURE_ADLS_GEN2_FILESYSTEM_PATH`: (Optional) Name of existing path in a [Data Lake Storage Gen2 filesystem](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction) for storing sample data with [access control lists](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control). Only used with the optional Data Lake Storage Gen2 [prep docs](#azure-data-lake-storage-gen2-prep-docs) script.

### Authentication behavior by environment

This application uses an in-memory token cache. User sessions are only available in memory while the application is running. When the application server is restarted, all users will need to log-in again.

The following table describes the impact of the `AZURE_USE_AUTHENTICATION` and `AZURE_ENFORCE_ACCESS_CONTROL` variables depending on the environment you are deploying the application in:

| AZURE_USE_AUTHENTICATION | AZURE_ENFORCE_ACCESS_CONTROL | Environment | Default Behavior |
|-|-|-|-|
| True | False | App Services | Use integrated auth <br /> Login page blocks access to app <br /> User can opt-into access control in developer settings <br /> Allows unrestricted access to sources |
| True | True | App Services | Use integrated auth <br /> Login page blocks access to app <br /> User must use access control |
| True | False | Local or Codespaces | Do not use integrated auth <br /> Can use app without login <br /> User can opt-into access control in developer settings <br /> Allows unrestricted access to sources |
| True | True | Local or Codespaces | Do not use integrated auth <br /> Cannot use app without login <br /> Behavior is chat box is greyed out with default “Please login message” <br /> User must use login button to make chat box usable <br /> User must use access control when logged in |
| False | False | All | No login or access control |
| False | True | All | Invalid setting |
