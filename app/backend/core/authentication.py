# Refactored from https://github.com/Azure-Samples/ms-identity-python-on-behalf-of

import json
import logging
from typing import Any, Optional

import aiohttp
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.models import SearchIndex
from jose import jwt
from msal import ConfidentialClientApplication
from msal.token_cache import TokenCache
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


# AuthError is raised when the authentication token sent by the client UI cannot be parsed or there is an authentication error accessing the graph API
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

    def __str__(self) -> str:
        return self.error or ""


class AuthenticationHelper:
    scope: str = "https://graph.microsoft.com/.default"

    def __init__(
        self,
        search_index: Optional[SearchIndex],
        use_authentication: bool,
        server_app_id: Optional[str],
        server_app_secret: Optional[str],
        client_app_id: Optional[str],
        tenant_id: Optional[str],
        require_access_control: bool = False,
    ):
        self.use_authentication = use_authentication
        self.server_app_id = server_app_id
        self.server_app_secret = server_app_secret
        self.client_app_id = client_app_id
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        # Depending on if requestedAccessTokenVersion is 1 or 2, the issuer and audience of the token may be different
        # See https://learn.microsoft.com/graph/api/resources/apiapplication
        self.valid_issuers = [
            f"https://sts.windows.net/{tenant_id}/",
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        ]
        self.valid_audiences = [f"api://{server_app_id}", str(server_app_id)]
        # See https://learn.microsoft.com/entra/identity-platform/access-tokens#validate-the-issuer for more information on token validation
        self.key_url = f"{self.authority}/discovery/v2.0/keys"

        if self.use_authentication:
            field_names = [field.name for field in search_index.fields] if search_index else []
            self.has_auth_fields = "oids" in field_names and "groups" in field_names
            self.require_access_control = require_access_control
            self.confidential_client = ConfidentialClientApplication(
                server_app_id, authority=self.authority, client_credential=server_app_secret, token_cache=TokenCache()
            )
        else:
            self.has_auth_fields = False
            self.require_access_control = False

    def get_auth_setup_for_client(self) -> dict[str, Any]:
        # returns MSAL.js settings used by the client app
        return {
            "useLogin": self.use_authentication,  # Whether or not login elements are enabled on the UI
            "requireAccessControl": self.require_access_control,  # Whether or not access control is required to use the application
            "msalConfig": {
                "auth": {
                    "clientId": self.client_app_id,  # Client app id used for login
                    "authority": self.authority,  # Directory to use for login https://learn.microsoft.com/azure/active-directory/develop/msal-client-application-configuration#authority
                    "redirectUri": "/redirect",  # Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
                    "postLogoutRedirectUri": "/",  # Indicates the page to navigate after logout.
                    "navigateToLoginRequestUrl": False,  # If "true", will navigate back to the original request location before processing the auth code response.
                },
                "cache": {
                    # Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.
                    "cacheLocation": "localStorage",
                    # Set this to "true" if you are having issues on IE11 or Edge
                    "storeAuthStateInCookie": False,
                },
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
        if auth:
            parts = auth.split()

            if parts[0].lower() != "bearer":
                raise AuthError(error="Authorization header must start with Bearer", status_code=401)
            elif len(parts) == 1:
                raise AuthError(error="Token not found", status_code=401)
            elif len(parts) > 2:
                raise AuthError(error="Authorization header must be Bearer token", status_code=401)

            token = parts[1]
            return token

        # App services built-in authentication passes the access token directly as a header
        # To learn more, please visit https://learn.microsoft.com/azure/app-service/configure-authentication-oauth-tokens
        token = headers.get("x-ms-token-aad-access-token", None)
        if token:
            return token

        raise AuthError(error="Authorization header is expected", status_code=401)

    def build_security_filters(self, overrides: dict[str, Any], auth_claims: dict[str, Any]):
        # Build different permutations of the oid or groups security filter using OData filters
        # https://learn.microsoft.com/azure/search/search-security-trimming-for-azure-search
        # https://learn.microsoft.com/azure/search/search-query-odata-filter
        use_oid_security_filter = self.require_access_control or overrides.get("use_oid_security_filter")
        use_groups_security_filter = self.require_access_control or overrides.get("use_groups_security_filter")

        if (use_oid_security_filter or use_groups_security_filter) and not self.has_auth_fields:
            raise AuthError(
                error="oids and groups must be defined in the search index to use authentication", status_code=400
            )

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
            # Validate the token before use
            await self.validate_access_token(auth_token)

            # Use the on-behalf-of-flow to acquire another token for use with Microsoft Graph
            # See https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow for more information
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
            logging.exception("Exception getting authorization information - " + json.dumps(e.error))
            if self.require_access_control:
                raise
            return {}
        except Exception:
            logging.exception("Exception getting authorization information")
            if self.require_access_control:
                raise
            return {}

    async def check_path_auth(self, path: str, auth_claims: dict[str, Any], search_client: SearchClient) -> bool:
        # Start with the standard security filter for all queries
        security_filter = self.build_security_filters(overrides={}, auth_claims=auth_claims)
        # If there was no security filter, then the path is allowed
        if not security_filter:
            return True

        # Filter down to only chunks that are from the specific source file
        filter = f"{security_filter} and (sourcepage eq '{path}')"

        # If the filter returns any results, the user is allowed to access the document
        # Otherwise, access is denied
        results = await search_client.search(search_text="*", top=1, filter=filter)
        allowed = False
        async for _ in results:
            allowed = True
            break

        return allowed

    # See https://github.com/Azure-Samples/ms-identity-python-on-behalf-of/blob/939be02b11f1604814532fdacc2c2eccd198b755/FlaskAPI/helpers/authorization.py#L44
    async def validate_access_token(self, token: str):
        """
        Validate an access token is issued by Entra
        """
        jwks = None
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(AuthError),
            wait=wait_random_exponential(min=15, max=60),
            stop=stop_after_attempt(5),
        ):
            with attempt:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=self.key_url) as resp:
                        resp_status = resp.status
                        if resp_status in [500, 502, 503, 504]:
                            raise AuthError(
                                error=f"Failed to get keys info: {await resp.text()}", status_code=resp_status
                            )
                        jwks = await resp.json()

        if not jwks or "keys" not in jwks:
            raise AuthError({"code": "invalid_keys", "description": "Unable to get keys to validate auth token."}, 401)

        rsa_key = None
        issuer = None
        audience = None
        try:
            unverified_header = jwt.get_unverified_header(token)
            unverified_claims = jwt.get_unverified_claims(token)
            issuer = unverified_claims.get("iss")
            audience = unverified_claims.get("aud")
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {"kty": key["kty"], "kid": key["kid"], "use": key["use"], "n": key["n"], "e": key["e"]}
                    break
        except Exception as exc:
            raise AuthError(
                {"code": "invalid_header", "description": "Unable to parse authorization token."}, 401
            ) from exc
        if not rsa_key:
            raise AuthError({"code": "invalid_header", "description": "Unable to find appropriate key"}, 401)

        if issuer not in self.valid_issuers:
            raise AuthError(
                {"code": "invalid_header", "description": f"Issuer {issuer} not in {','.join(self.valid_issuers)}"}, 401
            )

        if audience not in self.valid_audiences:
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": f"Audience {audience} not in {','.join(self.valid_audiences)}",
                },
                401,
            )

        try:
            jwt.decode(token, rsa_key, algorithms=["RS256"], audience=audience, issuer=issuer)
        except jwt.ExpiredSignatureError as jwt_expired_exc:
            raise AuthError({"code": "token_expired", "description": "token is expired"}, 401) from jwt_expired_exc
        except jwt.JWTClaimsError as jwt_claims_exc:
            raise AuthError(
                {"code": "invalid_claims", "description": "incorrect claims," "please check the audience and issuer"},
                401,
            ) from jwt_claims_exc
        except Exception as exc:
            raise AuthError(
                {"code": "invalid_header", "description": "Unable to parse authorization token."}, 401
            ) from exc
