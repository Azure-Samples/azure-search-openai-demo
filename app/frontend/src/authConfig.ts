// Refactored from https://github.com/Azure-Samples/ms-identity-javascript-react-tutorial/blob/main/1-Authentication/1-sign-in/SPA/src/authConfig.js

import { IPublicClientApplication } from "@azure/msal-browser";

const appServicesAuthTokenUrl = ".auth/me";
const appServicesAuthTokenRefreshUrl = ".auth/refresh";
const appServicesAuthLogoutUrl = ".auth/logout?post_logout_redirect_uri=/";

interface AppServicesToken {
    id_token: string;
    access_token: string;
    user_claims: Record<string, any>;
    expires_on: string;
}

interface AuthSetup {
    // Set to true if login elements should be shown in the UI
    useLogin: boolean;
    // Set to true if access control is enforced by the application
    requireAccessControl: boolean;
    // Set to true if the application allows unauthenticated access (only applies for documents without access control)
    enableUnauthenticatedAccess: boolean;
    /**
     * Configuration object to be passed to MSAL instance on creation.
     * For a full list of MSAL.js configuration parameters, visit:
     * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
     */
    msalConfig: {
        auth: {
            clientId: string; // Client app id used for login
            authority: string; // Directory to use for login https://learn.microsoft.com/entra/identity-platform/msal-client-application-configuration#authority
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
         * https://learn.microsoft.com/entra/identity-platform/permissions-consent-overview#openid-connect-scopes
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

export const enableUnauthenticatedAccess = authSetup.enableUnauthenticatedAccess;

export const requireLogin = requireAccessControl && !enableUnauthenticatedAccess;

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
 * https://learn.microsoft.com/entra/identity-platform/permissions-consent-overview#openid-connect-scopes
 */
export const loginRequest = authSetup.loginRequest;

const tokenRequest = authSetup.tokenRequest;

// Build an absolute redirect URI using the current window's location and the relative redirect URI from auth setup
export const getRedirectUri = () => {
    return window.location.origin + authSetup.msalConfig.auth.redirectUri;
};

// Cache the app services token if it's available
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/this#global_context
declare global {
    var cachedAppServicesToken: AppServicesToken | null;
}
globalThis.cachedAppServicesToken = null;

/**
 * Retrieves an access token if the user is logged in using app services authentication.
 * Checks if the current token is expired and fetches a new token if necessary.
 * Returns null if the app doesn't support app services authentication.
 *
 * @returns {Promise<AppServicesToken | null>} A promise that resolves to an AppServicesToken if the user is authenticated, or null if authentication is not supported or fails.
 */
const getAppServicesToken = (): Promise<AppServicesToken | null> => {
    const checkNotExpired = (appServicesToken: AppServicesToken) => {
        const currentDate = new Date();
        const expiresOnDate = new Date(appServicesToken.expires_on);
        return expiresOnDate > currentDate;
    };

    if (globalThis.cachedAppServicesToken && checkNotExpired(globalThis.cachedAppServicesToken)) {
        return Promise.resolve(globalThis.cachedAppServicesToken);
    }

    const getAppServicesTokenFromMe: () => Promise<AppServicesToken | null> = () => {
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
                            }, {}) as Record<string, any>,
                            expires_on: json[0]["expires_on"] as string
                        } as AppServicesToken;
                    }

                    return null;
                });
            }

            return null;
        });
    };

    return getAppServicesTokenFromMe().then(token => {
        if (token) {
            if (checkNotExpired(token)) {
                globalThis.cachedAppServicesToken = token;
                return token;
            }

            return fetch(appServicesAuthTokenRefreshUrl).then(r => {
                if (r.ok) {
                    return getAppServicesTokenFromMe();
                }
                return null;
            });
        }

        return null;
    });
};

export const isUsingAppServicesLogin = (await getAppServicesToken()) != null;

// Sign out of app services
// Learn more at https://learn.microsoft.com/azure/app-service/configure-authentication-customize-sign-in-out#sign-out-of-a-session
export const appServicesLogout = () => {
    window.location.href = appServicesAuthLogoutUrl;
};

/**
 * Determines if the user is logged in either via the MSAL public client application or the app services login.
 * @param {IPublicClientApplication | undefined} client - The MSAL public client application instance, or undefined if not available.
 * @returns {Promise<boolean>} A promise that resolves to true if the user is logged in, false otherwise.
 */
export const checkLoggedIn = async (client: IPublicClientApplication | undefined): Promise<boolean> => {
    if (client) {
        const activeAccount = client.getActiveAccount();
        if (activeAccount) {
            return true;
        }
    }

    const appServicesToken = await getAppServicesToken();
    if (appServicesToken) {
        return true;
    }

    return false;
};

// Get an access token for use with the API server.
// ID token received when logging in may not be used for this purpose because it has the incorrect audience
// Use the access token from app services login if available
export const getToken = async (client: IPublicClientApplication): Promise<string | undefined> => {
    const appServicesToken = await getAppServicesToken();
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

/**
 * Retrieves the username of the active account.
 * If no active account is found, attempts to retrieve the username from the app services login token if available.
 * @param {IPublicClientApplication} client - The MSAL public client application instance.
 * @returns {Promise<string | null>} The username of the active account, or null if no username is found.
 */
export const getUsername = async (client: IPublicClientApplication): Promise<string | null> => {
    const activeAccount = client.getActiveAccount();
    if (activeAccount) {
        return activeAccount.username;
    }

    const appServicesToken = await getAppServicesToken();
    if (appServicesToken?.user_claims) {
        return appServicesToken.user_claims.preferred_username;
    }

    return null;
};

/**
 * Retrieves the token claims of the active account.
 * If no active account is found, attempts to retrieve the token claims from the app services login token if available.
 * @param {IPublicClientApplication} client - The MSAL public client application instance.
 * @returns {Promise<Record<string, unknown> | undefined>} A promise that resolves to the token claims of the active account, the user claims from the app services login token, or undefined if no claims are found.
 */
export const getTokenClaims = async (client: IPublicClientApplication): Promise<Record<string, unknown> | undefined> => {
    const activeAccount = client.getActiveAccount();
    if (activeAccount) {
        return activeAccount.idTokenClaims;
    }

    const appServicesToken = await getAppServicesToken();
    if (appServicesToken) {
        return appServicesToken.user_claims;
    }

    return undefined;
};
