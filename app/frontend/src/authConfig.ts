// Refactored from https://github.com/Azure-Samples/ms-identity-javascript-react-tutorial/blob/main/1-Authentication/1-sign-in/SPA/src/authConfig.js

import { IPublicClientApplication } from "@azure/msal-browser";

const appServicesAuthTokenUrl = ".auth/me";
const appServicesAuthTokenRefreshUrl = ".auth/refresh";
const appServicesAuthLogoutUrl = ".auth/logout?post_logout_redirect_uri=/";

interface AppServicesToken {
    id_token: string;
    access_token: string;
    user_claims: Record<string, any>;
}

interface AuthSetup {
    // Set to true if login elements should be shown in the UI
    useLogin: boolean;
    // Set to true if access control is enforced by the application
    requireAccessControl: boolean;
    /**
     * Configuration object to be passed to MSAL instance on creation.
     * For a full list of MSAL.js configuration parameters, visit:
     * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
     */
    msalConfig: {
        auth: {
            clientId: string; // Client app id used for login
            authority: string; // Directory to use for login https://learn.microsoft.com/azure/active-directory/develop/msal-client-application-configuration#authority
            redirectUri: string; // Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
            postLogoutRedirectUri: string; // Indicates the page to navigate after logout.
            navigateToLoginRequestUrl: boolean; // If "true", will navigate back to the original request location before processing the auth code response.
        };
        cache: {
            cacheLocation: string; // Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.
            storeAuthStateInCookie: boolean; // Set this to "true" if you are having issues on IE11 or Edge
        };
    };
    loginRequest: {
        /**
         * Scopes you add here will be prompted for user consent during sign-in.
         * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
         * For more information about OIDC scopes, visit:
         * https://docs.microsoft.com/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
         */
        scopes: Array<string>;
    };
    tokenRequest: {
        scopes: Array<string>;
    };
}

// Fetch the auth setup JSON data from the API if not already cached
async function fetchAuthSetup(): Promise<AuthSetup> {
    const response = await fetch("/auth_setup");
    if (!response.ok) {
        throw new Error(`auth setup response was not ok: ${response.status}`);
    }
    return await response.json();
}

const authSetup = await fetchAuthSetup();

export const useLogin = authSetup.useLogin;

export const requireAccessControl = authSetup.requireAccessControl;

/**
 * Configuration object to be passed to MSAL instance on creation.
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig = authSetup.msalConfig;

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 * For more information about OIDC scopes, visit:
 * https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
 */
export const loginRequest = authSetup.loginRequest;

const tokenRequest = authSetup.tokenRequest;

// Build an absolute redirect URI using the current window's location and the relative redirect URI from auth setup
export const getRedirectUri = () => {
    return window.location.origin + authSetup.msalConfig.auth.redirectUri;
};

// Get an access token if a user logged in using app services authentication
// Returns null if the app doesn't support app services authentication
const getAppServicesToken = (): Promise<AppServicesToken | null> => {
    return fetch(appServicesAuthTokenRefreshUrl).then(r => {
        if (r.ok) {
            return fetch(appServicesAuthTokenUrl).then(r => {
                if (r.ok) {
                    return r.json().then(json => {
                        if (json.length > 0) {
                            return {
                                id_token: json[0]["id_token"] as string,
                                access_token: json[0]["access_token"] as string,
                                user_claims: json[0]["user_claims"].reduce((acc: Record<string, any>, item: Record<string, any>) => {
                                    acc[item.typ] = item.val;
                                    return acc;
                                }, {}) as Record<string, any>
                            };
                        }

                        return null;
                    });
                }

                return null;
            });
        }

        return null;
    });
};

export const appServicesToken = await getAppServicesToken();

// Sign out of app services
// Learn more at https://learn.microsoft.com/azure/app-service/configure-authentication-customize-sign-in-out#sign-out-of-a-session
export const appServicesLogout = () => {
    window.location.href = appServicesAuthLogoutUrl;
};

// Determine if the user is logged in
// The user may have logged in either using the app services login or the on-page login
export const isLoggedIn = (client: IPublicClientApplication | undefined): boolean => {
    return client?.getActiveAccount() != null || appServicesToken != null;
};

// Get an access token for use with the API server.
// ID token received when logging in may not be used for this purpose because it has the incorrect audience
// Use the access token from app services login if available
export const getToken = (client: IPublicClientApplication): Promise<string | undefined> => {
    if (appServicesToken) {
        return Promise.resolve(appServicesToken.access_token);
    }

    return client
        .acquireTokenSilent({
            ...tokenRequest,
            redirectUri: getRedirectUri()
        })
        .then(r => r.accessToken)
        .catch(error => {
            console.log(error);
            return undefined;
        });
};
