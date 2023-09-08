import { AuthenticationResult, IPublicClientApplication } from "@azure/msal-browser";

/*
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
 */

export const useLogin = true; // Set to true to enable login

// Get an access token for use with the API server.
// ID token received when logging in may not be used for this purpose because it has the incorrect audience
export const getToken = (client: IPublicClientApplication): Promise<AuthenticationResult> => {
    return client.acquireTokenSilent({
        ...loginRequest,
        redirectUri: '/redirect'
    })
}

/**
 * Configuration object to be passed to MSAL instance on creation. 
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md 
 */
export const msalConfig = {
    auth: {
        clientId: 'c06098e2-79e4-4e6c-8e43-f8b0e7728349', // Replace with your client app id
        authority: `https://login.microsoftonline.com/72f988bf-86f1-41af-91ab-2d7cd011db47`, // Defaults to "https://login.microsoftonline.com/common"
        redirectUri: '/', // Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
        postLogoutRedirectUri: '/', // Indicates the page to navigate after logout.
        navigateToLoginRequestUrl: false, // If "true", will navigate back to the original request location before processing the auth code response.
    },
    cache: {
        cacheLocation: 'sessionStorage', // Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.
        storeAuthStateInCookie: false, // Set this to "true" if you are having issues on IE11 or Edge
    }
};

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 * For more information about OIDC scopes, visit: 
 * https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
 */
export const loginRequest = {
    scopes: [`api://201ac4a0-3323-43ed-a024-bf37eaedc7bf/.default`] // Replace the app id with your server app id
};
