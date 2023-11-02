# Refactored from https://github.com/Azure-Samples/ms-identity-python-on-behalf-of

import json
import logging
import os
from tempfile import TemporaryDirectory
from typing import Any, Optional

import aiohttp
from msal import ConfidentialClientApplication
from msal_extensions import (
    FilePersistence,
    PersistedTokenCache,
    build_encrypted_persistence,
)


# AuthError is raised when the authentication token sent by the client UI cannot be parsed or there is an authentication error accessing the graph API
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


class AuthenticationHelper:
    scope: str = "https://graph.microsoft.com/.default"

    def __init__(
        self,
        use_authentication: bool,
        server_app_id: Optional[str],
        server_app_secret: Optional[str],
        client_app_id: Optional[str],
        tenant_id: Optional[str],
        token_cache_path: Optional[str] = None,
    ):
        self.use_authentication = use_authentication
        self.server_app_id = server_app_id
        self.server_app_secret = server_app_secret
        self.client_app_id = client_app_id
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"

        if self.use_authentication:
            self.token_cache_path = token_cache_path
            if not self.token_cache_path:
                self.temporary_directory = TemporaryDirectory()
                self.token_cache_path = os.path.join(self.temporary_directory.name, "token_cache.bin")
            try:
                persistence = build_encrypted_persistence(location=self.token_cache_path)
            except Exception:
                logging.exception("Encryption unavailable. Opting in to plain text.")
                persistence = FilePersistence(location=self.token_cache_path)
            self.confidential_client = ConfidentialClientApplication(
                server_app_id,
                authority=self.authority,
                client_credential=server_app_secret,
                token_cache=PersistedTokenCache(persistence),
            )

    def get_auth_setup_for_client(self) -> dict[str, Any]:
        # returns MSAL.js settings used by the client app
        return {
            "useLogin": self.use_authentication,  # Whether or not login elements are enabled on the UI
            "msalConfig": {
                "auth": {
                    "clientId": self.client_app_id,  # Client app id used for login
                    "authority": self.authority,  # Directory to use for login https://learn.microsoft.com/azure/active-directory/develop/msal-client-application-configuration#authority
                    "redirectUri": "/redirect",  # Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
                    "postLogoutRedirectUri": "/",  # Indicates the page to navigate after logout.
                    "navigateToLoginRequestUrl": False,  # If "true", will navigate back to the original request location before processing the auth code response.
                },
                "cache": {
                    "cacheLocation": "sessionStorage",
                    "storeAuthStateInCookie": False,
                },  # Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.  # Set this to "true" if you are having issues on IE11 or Edge
            },
            "loginRequest": {
                # Scopes you add here will be prompted for user consent during sign-in.
                # By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
                # For more information about OIDC scopes, visit:
                # https://docs.microsoft.com/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
                "scopes": [".default"],
                # Uncomment the following line to cause a consent dialog to appear on every login
                # For more information, please visit https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow#request-an-authorization-code
                # "prompt": "consent"
            },
            "tokenRequest": {
                "scopes": [f"api://{self.server_app_id}/access_as_user"],
            },
        }

    @staticmethod
    def get_token_auth_header(headers: dict) -> str:
        # Obtains the Access Token from the Authorization Header
        auth = headers.get("Authorization", None)
        if not auth:
            raise AuthError(
                {"code": "authorization_header_missing", "description": "Authorization header is expected"}, 401
            )

        parts = auth.split()

        if parts[0].lower() != "bearer":
            raise AuthError(
                {"code": "invalid_header", "description": "Authorization header must start with Bearer"}, 401
            )
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

        oid_security_filter = (
            "oids/any(g:search.in(g, '{}'))".format(auth_claims.get("oid") or "") if use_oid_security_filter else None
        )
        groups_security_filter = (
            "groups/any(g:search.in(g, '{}'))".format(", ".join(auth_claims.get("groups") or []))
            if use_groups_security_filter
            else None
        )

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
    async def list_groups(graph_resource_access_token: dict) -> list[str]:
        headers = {"Authorization": "Bearer " + graph_resource_access_token["access_token"]}
        groups = []
        async with aiohttp.ClientSession(headers=headers) as session:
            resp_json = None
            resp_status = None
            async with session.get(url="https://graph.microsoft.com/v1.0/me/transitiveMemberOf?$select=id") as resp:
                resp_json = await resp.json()
                resp_status = resp.status
                if resp_status != 200:
                    raise AuthError(error=json.dumps(resp_json), status_code=resp_status)

            while resp_status == 200:
                value = resp_json["value"]
                for group in value:
                    groups.append(group["id"])
                next_link = resp_json.get("@odata.nextLink")
                if next_link:
                    async with session.get(url=next_link) as resp:
                        resp_json = await resp.json()
                        resp_status = resp.status
                else:
                    break
            if resp_status != 200:
                raise AuthError(error=json.dumps(resp_json), status_code=resp_status)

        return groups

    async def get_auth_claims_if_enabled(self, headers: dict) -> dict[str, Any]:
        if not self.use_authentication:
            return {}
        try:
            # Read the authentication token from the authorization header and exchange it using the On Behalf Of Flow
            # The scope is set to the Microsoft Graph API, which may need to be called for more authorization information
            # https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow
            auth_token = AuthenticationHelper.get_token_auth_header(headers)
            graph_resource_access_token = self.confidential_client.acquire_token_on_behalf_of(
                user_assertion=auth_token, scopes=["https://graph.microsoft.com/.default"]
            )
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
            has_group_overage_claim = (
                missing_groups_claim
                and "_claim_names" in id_token_claims
                and "groups" in id_token_claims["_claim_names"]
            )
            if missing_groups_claim or has_group_overage_claim:
                # Read the user's groups from Microsoft Graph
                auth_claims["groups"] = await AuthenticationHelper.list_groups(graph_resource_access_token)
            return auth_claims
        except AuthError as e:
            print(e.error)
            logging.exception("Exception getting authorization information - " + json.dumps(e.error))
            return {}
        except Exception:
            logging.exception("Exception getting authorization information")
            return {}
