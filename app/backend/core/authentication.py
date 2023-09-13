# Refactored from https://github.com/Azure-Samples/ms-identity-python-on-behalf-of

from quart import request
from abc import ABC
import msal, os
from msgraph import GraphServiceClient
from azure.core.credentials import TokenCredential, AccessToken
import logging
from typing import Any

class AuthError(Exception):
    error: str = None
    status_code: int = None

    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

# TokenCredential wrapper class to use an auth token to call the Microsoft Graph API
class AuthToken(TokenCredential):
    _token: dict = None

    def __init__(self, token: dict):
        self._token = token

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        return AccessToken(self._token["access_token"], self._token["expires_in"])


class AuthenticationHelper(ABC):

    _confidential_client: msal.ConfidentialClientApplication = None
    _authority: str = "https://login.microsoftonline.com/{}".format(os.getenv("AZURE_TENANT_ID"))

    @staticmethod
    def use_authentication():
        # Checks for environment variables related to authentication.
        # If they are not defined, authentication is not used
        var_names = ["AZURE_USE_AUTHENTICATION", "AZURE_SERVER_APP_ID", "AZURE_SERVER_APP_SECRET", "AZURE_CLIENT_APP_ID", "AZURE_TENANT_ID"]
        return all(var_name in os.environ for var_name in var_names)

    @staticmethod
    def get_auth_setup_for_client() -> dict[str, Any]:
        # returns MSAL.js settings used by the client app
        return {
            "useLogin": AuthenticationHelper.use_authentication(), # Whether or not login elements are enabled on the UI
            "msalConfig": {
                "auth": {
                    "clientId": os.getenv("AZURE_CLIENT_APP_ID"), # Client app id used for login
                    "authority": AuthenticationHelper._authority, # Directory to use for login https://learn.microsoft.com/azure/active-directory/develop/msal-client-application-configuration#authority
                    "redirectUri": "/redirect", # Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
                    "postLogoutRedirectUri": "/", # Indicates the page to navigate after logout.
                    "navigateToLoginRequestUrl": False # If "true", will navigate back to the original request location before processing the auth code response.
                },
                "cache": {
                    "cacheLocation": "sessionStorage", # Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.
                    "storeAuthStateInCookie": False # Set this to "true" if you are having issues on IE11 or Edge
                }
            },
            "loginRequest": {
                # Scopes you add here will be prompted for user consent during sign-in.
                # By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
                # For more information about OIDC scopes, visit:
                # https://docs.microsoft.com/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
                "scopes": ["api://{}/.default".format(os.getenv("AZURE_SERVER_APP_ID"))]
            }
        }

    @staticmethod
    def get_token_auth_header() -> str:
        # Obtains the Access Token from the Authorization Header
        auth = request.headers.get("Authorization", None)
        if not auth:
            raise AuthError({"code": "authorization_header_missing",
                            "description":
                            "Authorization header is expected"}, 401)

        parts = auth.split()

        if parts[0].lower() != "bearer":
            raise AuthError({"code": "invalid_header",
                            "description": "Authorization header must start with Bearer"}, 401)
        elif len(parts) == 1:
            raise AuthError({"code": "invalid_header",
                            "description": "Token not found"}, 401)
        elif len(parts) > 2:
            raise AuthError({"code": "invalid_header",
                            "description": "Authorization header must be Bearer token"}, 401)

        token = parts[1]
        return token

    @staticmethod
    def get_confidential_client():
        # This example only uses the default memory token cache and should not be used for production
        if AuthenticationHelper._confidential_client is None:
            AuthenticationHelper._confidential_client = msal.ConfidentialClientApplication(
                os.getenv("AZURE_SERVER_APP_ID"),
                authority=AuthenticationHelper._authority,
                client_credential=os.getenv("AZURE_SERVER_APP_SECRET"))

        return AuthenticationHelper._confidential_client

    @staticmethod
    def build_security_filters(overrides: dict[str, Any], auth_claims: dict[str, Any]):
        # Build different permutations of the oid or groups security filter using OData filters
        # https://learn.microsoft.com/azure/search/search-security-trimming-for-azure-search
        # https://learn.microsoft.com/azure/search/search-query-odata-filter
        use_oid_security_filter = overrides.get("use_oid_security_filter")
        use_groups_security_filter = overrides.get("use_groups_security_filter")

        oid_security_filter = "oids/any(g:search.in(g, '{}'))".format(auth_claims["oid"]) if use_oid_security_filter else None
        groups_security_filter = "groups/any(g:search.in(g, '{}'))".format(", ".join(auth_claims["groups"])) if use_groups_security_filter else None

        # If only one security filter is specified, return that filter
        # If both security filters are specified, combine them with "or" so only 1 security filter needs to pass
        # If no security filters are specified, don't return any filter
        if oid_security_filter and not groups_security_filter:
            return oid_security_filter
        elif groups_security_filter and not oid_security_filter:
            return groups_security_filter
        elif oid_security_filter and groups_security_filter:
            return "({} or {})".format(oid_security_filter, groups_security_filter)
        else:
            return None

    @staticmethod
    async def get_auth_claims_if_enabled() -> dict[str: Any]:
        if AuthenticationHelper.use_authentication():
            try:
                # Read the authentication token from the authorization header and exchange it using the On Behalf Of Flow
                # The scope is set to the Microsoft Graph API, which may need to be called for more authorization information
                # https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow
                auth_token = AuthenticationHelper.get_token_auth_header()
                graph_resource_access_token = AuthenticationHelper.get_confidential_client().acquire_token_on_behalf_of(
                    user_assertion=auth_token,
                    scopes=["https://graph.microsoft.com/.default"]
                )
                if 'error' in graph_resource_access_token:
                    raise AuthError(error=str(graph_resource_access_token), status_code=401)

                # Read the claims from the response. The oid and groups claims are used for security filtering
                # https://learn.microsoft.com/azure/active-directory/develop/id-token-claims-reference
                id_token_claims = graph_resource_access_token["id_token_claims"]
                auth_claims = { "oid": id_token_claims["oid"], "groups": id_token_claims.get("groups") or [] }

                # A groups claim may have been omitted either because it was not added in the application manifest for the API application,
                # or a groups overage claim may have been emitted.
                # https://learn.microsoft.com/azure/active-directory/develop/id-token-claims-reference#groups-overage-claim
                missing_groups_claim = "groups" not in id_token_claims
                has_group_overage_claim = missing_groups_claim and \
                    "_claim_names" in id_token_claims and \
                    "groups" in id_token_claims["_claim_names"]
                if missing_groups_claim or has_group_overage_claim:
                    # Read the user's groups from Microsoft Graph
                    client = GraphServiceClient(credentials=AuthToken(graph_resource_access_token))
                    user_groups = await client.me.member_of.get()
                    for group in user_groups.value:
                        auth_claims["groups"].append(group.id)
                return auth_claims
            except:
                logging.exception("Exception getting authorization information")

        return {}
