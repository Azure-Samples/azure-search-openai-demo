# Refactored from https://github.com/Azure-Samples/ms-identity-python-on-behalf-of

from quart import request
from abc import ABC
import msal, os
from msgraph import GraphServiceClient
from azure.core.credentials import TokenCredential, AccessToken
import asyncio

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

class AuthToken(TokenCredential):
    _token: dict = None

    def __init__(self, token: dict):
        self._token = token

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        return AccessToken(self._token["access_token"], self._token["expires_in"])


class AuthenticationHelper(ABC):

    _confidential_client: msal.ConfidentialClientApplication = None

    @staticmethod
    def use_authentication():
        # Checks for environment variables related to authentication.
        # If they are not defined, authentication is not used.
        return os.getenv("CLIENT_ID") and os.getenv("AUTHORITY") and os.getenv("CLIENT_SECRET")

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
                os.getenv("CLIENT_ID"),
                authority=os.getenv("AUTHORITY"),
                client_credential=os.getenv("CLIENT_SECRET"))
        
        return AuthenticationHelper._confidential_client

    @staticmethod
    async def get_auth_claims_if_enabled() -> str:
        auth_claims = {}
        if AuthenticationHelper.use_authentication():
            auth_token = AuthenticationHelper.get_token_auth_header()
            graph_resource_access_token = AuthenticationHelper.get_confidential_client().acquire_token_on_behalf_of(
                user_assertion=auth_token,
                scopes=["https://graph.microsoft.com/.default"]
            )
            print(graph_resource_access_token)
            auth_claims = graph_resource_access_token["id_token_claims"]
            client = GraphServiceClient(credentials=AuthToken(graph_resource_access_token))
            user = await client.me.get()
            print(user.user_principal_name, user.display_name, user.id)
        print(auth_claims)
        return auth_claims
