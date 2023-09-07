import { useMsal } from "@azure/msal-react";

/*
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
 */

export const useLogin = true;

// Validate claim used for filters is present, before allowing the user to select that claim as an option
export const checkClaim = (claim: string) => {
    const idTokenClaims = useMsal().instance?.getActiveAccount()?.idTokenClaims ?? {}
    if (claim == "groups") {
        // Check for groups overage claim in addition to a normal groups claim
        // https://learn.microsoft.com/azure/active-directory/develop/id-token-claims-reference#groups-overage-claim
        if ("_claim_names" in idTokenClaims &&
            "groups" in (idTokenClaims["_claim_names"] as object)) {
            return true;
        }
    }

    return claim in idTokenClaims;
}

/**
 * Configuration object to be passed to MSAL instance on creation. 
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md 
 */
export const msalConfig = {
    auth: {
        clientId: 'f153bbec-e5c2-4f4e-85ae-0e9a80c1d337', // This is the ONLY mandatory field that you need to supply.
        authority: 'https://login.microsoftonline.com/72f988bf-86f1-41af-91ab-2d7cd011db47', // Defaults to "https://login.microsoftonline.com/common"
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
    scopes: ["openid", "profile", "email"]
};

/**
 * An optional silentRequest object can be used to achieve silent SSO
 * between applications by providing a "login_hint" property.
 */
export const silentRequest = {
    scopes: ["openid", "profile"],
    loginHint: "example@domain.net"
};