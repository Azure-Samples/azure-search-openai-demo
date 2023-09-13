# Refactored from https://github.com/Azure-Samples/ms-identity-python-on-behalf-of

import logging
import os
from typing import Any

from msal import ConfidentialClientApplication
from msal_extensions import build_encrypted_persistence, PersistedTokenCache
import urllib3
from quart import request
from tempfile import TemporaryDirectory


# AuthError is raised when the authentication token sent by the client UI cannot be parsed
class AuthError(Exception):
    error: str = None
    status_code: int = None

    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


class AuthenticationHelper():
    _confidential_client: ConfidentialClientApplication = None
    _authority: str = None
    _use_authentication: bool = False
    _server_app_id: str = None
    _server_app_secret: str = None
    _client_app_id: str = None
    _tenant_id: str = None
    _token_cache_path: str = None
    _temporary_directory: TemporaryDirectory = None

    def __init__(self, use_authentication: bool, server_app_id: str, server_app_secret: str, client_app_id: str, tenant_id: str, token_cache_path: str):
        self._use_authentication = use_authentication
        self._server_app_id = server_app_id
        self._server_app_secret = server_app_secret
        self._client_app_id = client_app_id
        self._tenant_id = tenant_id
        self._authority = "https://login.microsoftonline.com/{}".format(tenant_id)

        if self._use_authentication:
            self._token_cache_path = token_cache_path
            if not self._token_cache_path:
                self._temporary_directory = TemporaryDirectory()
                self._token_cache_path = os.path.join(self._temporary_directory.name, "token_cache.bin")
            persistence = build_encrypted_persistence(location=self._token_cache_path)
            self._confidential_client = ConfidentialClientApplication(server_app_id, authority=self._authority, client_credential=server_app_secret, token_cache=PersistedTokenCache(persistence))

    def use_authentication(self):
        return self._use_authentication

    def get_auth_setup_for_client(self) -> dict[str, Any]:
        # returns MSAL.js settings used by the client app
        return {
            "useLogin": self._use_authentication,  # Whether or not login elements are enabled on the UI
            "msalConfig": {
                "auth": {
                    "clientId": self._client_app_id,  # Client app id used for login
                    "authority": self._authority,  # Directory to use for login https://learn.microsoft.com/azure/active-directory/develop/msal-client-application-configuration#authority
                    "redirectUri": "/redirect",  # Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
                    "postLogoutRedirectUri": "/",  # Indicates the page to navigate after logout.
                    "navigateToLoginRequestUrl": False,  # If "true", will navigate back to the original request location before processing the auth code response.
                },
                "cache": {"cacheLocation": "sessionStorage", "storeAuthStateInCookie": False},  # Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.  # Set this to "true" if you are having issues on IE11 or Edge
            },
            "loginRequest": {
                # Scopes you add here will be prompted for user consent during sign-in.
                # By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
                # For more information about OIDC scopes, visit:
                # https://docs.microsoft.com/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
                "scopes": ["api://{}/.default".format(self._server_app_id)]
            },
        }

    @staticmethod
    def get_token_auth_header() -> str:
        # Obtains the Access Token from the Authorization Header
        auth = request.headers.get("Authorization", None)
        if not auth:
            raise AuthError({"code": "authorization_header_missing", "description": "Authorization header is expected"}, 401)

        parts = auth.split()

        if parts[0].lower() != "bearer":
            raise AuthError({"code": "invalid_header", "description": "Authorization header must start with Bearer"}, 401)
        elif len(parts) == 1:
            raise AuthError({"code": "invalid_header", "description": "Token not found"}, 401)
        elif len(parts) > 2:
            raise AuthError({"code": "invalid_header", "description": "Authorization header must be Bearer token"}, 401)

        token = parts[1]
        return token

    @staticmethod
    def build_security_filters(overrides: dict[str, Any], auth_claims: dict[str, Any]):
        # Build different permutations of the oid or groups security filter using OData filters
        # https://learn.microsoft.com/azure/search/search-security-trimming-for-azure-search
        # https://learn.microsoft.com/azure/search/search-query-odata-filter
        use_oid_security_filter = overrides.get("use_oid_security_filter")
        use_groups_security_filter = overrides.get("use_groups_security_filter")

        oid_security_filter = "oids/any(g:search.in(g, '{}'))".format(auth_claims.get("oid") or "") if use_oid_security_filter else None
        groups_security_filter = "groups/any(g:search.in(g, '{}'))".format(", ".join(auth_claims.get("groups") or [])) if use_groups_security_filter else None

        # If only one security filter is specified, return that filter
        # If both security filters are specified, combine them with "or" so only 1 security filter needs to pass
        # If no security filters are specified, don't return any filter
        if oid_security_filter and not groups_security_filter:
            return oid_security_filter
        elif groups_security_filter and not oid_security_filter:
            return groups_security_filter
        elif oid_security_filter and groups_security_filter:
            return f"({oid_security_filter} or {groups_security_filter})"
        else:
            return None

    @staticmethod
    async def list_groups(graph_resource_access_token: str) -> [str]:
        headers = {"Authorization": "Bearer " + graph_resource_access_token["access_token"]}
        resp = urllib3.request("GET", "https://graph.microsoft.com/v1.0/me/memberOf?$select=id", headers=headers, timeout=urllib3.Timeout(connect=10, read=10))
        groups = []
        while resp.status == 200:
            value = resp.json()["value"]
            for group in value:
                groups.append(group["id"])
            nextLink = resp.json().get("@odata.nextLink")
            if nextLink:
                resp = urllib3.request("GET", nextLink, headers=headers, timeout=urllib3.Timeout(connect=10, read=10))
            else:
                break

        return groups

    async def get_auth_claims_if_enabled(self) -> dict[str:Any]:
        if not self._use_authentication:
            return {}
        try:
            # Read the authentication token from the authorization header and exchange it using the On Behalf Of Flow
            # The scope is set to the Microsoft Graph API, which may need to be called for more authorization information
            # https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow
            auth_token = AuthenticationHelper.get_token_auth_header()
            graph_resource_access_token = self._confidential_client.acquire_token_on_behalf_of(user_assertion=auth_token, scopes=["https://graph.microsoft.com/.default"])
            if "error" in graph_resource_access_token:
                raise AuthError(error=str(graph_resource_access_token), status_code=401)

            # Read the claims from the response. The oid and groups claims are used for security filtering
            # https://learn.microsoft.com/azure/active-directory/develop/id-token-claims-reference
            id_token_claims = graph_resource_access_token["id_token_claims"]
            auth_claims = {"oid": id_token_claims["oid"], "groups": id_token_claims.get("groups") or []}

            # A groups claim may have been omitted either because it was not added in the application manifest for the API application,
            # or a groups overage claim may have been emitted.
            # https://learn.microsoft.com/azure/active-directory/develop/id-token-claims-reference#groups-overage-claim
            missing_groups_claim = "groups" not in id_token_claims
            has_group_overage_claim = missing_groups_claim and "_claim_names" in id_token_claims and "groups" in id_token_claims["_claim_names"]
            if missing_groups_claim or has_group_overage_claim:
                # Read the user's groups from Microsoft Graph
                auth_claims["groups"] = await AuthenticationHelper.list_groups(graph_resource_access_token)
            return auth_claims
        except Exception:
            logging.exception("Exception getting authorization information")
