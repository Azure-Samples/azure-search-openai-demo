import asyncio
import datetime
import os
import random
import subprocess
from typing import Any, Dict, Tuple

import aiohttp
from azure.identity.aio import AzureDeveloperCliCredential

from auth_common import (
    TIMEOUT,
    get_application,
    get_auth_headers,
    test_authentication_enabled,
    update_application,
)


async def create_application(auth_headers: Dict[str, str], app_payload: Dict[str, Any]) -> Tuple[str, str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post("https://graph.microsoft.com/v1.0/applications", json=app_payload) as response:
            if response.status != 201:
                raise Exception(await response.json())
            response_json = await response.json()
            object_id = response_json["id"]
            client_id = response_json["appId"]

        async with session.post(
            "https://graph.microsoft.com/v1.0/servicePrincipals",
            json={"appId": client_id, "displayName": app_payload["displayName"]},
        ) as response:
            if response.status != 201:
                raise Exception(await response.json())

    return object_id, client_id


async def add_client_secret(auth_headers: Dict[str, str], object_id: str):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            f"https://graph.microsoft.com/v1.0/applications/{object_id}/addPassword",
            json={"passwordCredential": {"displayName": "secret"}},
        ) as response:
            response_json = await response.json()
            if response.status == 200:
                return response_json["secretText"]

            raise Exception(response_json)


async def create_or_update_application_with_secret(
    auth_headers: Dict[str, str], app_id_env_var: str, app_secret_env_var: str, app_payload: Dict[str, Any]
) -> Tuple[str, str, bool]:
    app_id = os.getenv(app_id_env_var, "no-id")
    created_app = False
    object_id = None
    if app_id != "no-id":
        print(f"Checking if application {app_id} exists")
        object_id = await get_application(auth_headers, app_id)

    if object_id:
        print("Application already exists, not creating new one")
        await update_application(auth_headers, object_id, app_payload)
    else:
        print("Creating application registration")
        object_id, app_id = await create_application(auth_headers, app_payload)
        update_azd_env(app_id_env_var, app_id)
        created_app = True

    if object_id and os.getenv(app_secret_env_var, "no-secret") == "no-secret":
        print(f"Adding client secret to {app_id}")
        client_secret = await add_client_secret(auth_headers, object_id)
        update_azd_env(app_secret_env_var, client_secret)

    return (object_id, app_id, created_app)


def update_azd_env(name, val):
    subprocess.run(f"azd env set {name} {val}", shell=True)


def random_app_identifier():
    rand = random.Random()
    rand.seed(datetime.datetime.now().timestamp())
    return rand.randint(1000, 100000)


def create_server_app_initial_payload(identifier: int):
    return {
        "displayName": f"Azure Search OpenAI Chat Server App {identifier}",
        "signInAudience": "AzureADMyOrg",
    }


def create_server_app_permission_setup_payload(server_app_id: str):
    return {
        "api": {
            "knownClientApplications": [],
            "oauth2PermissionScopes": [
                {
                    "id": "7b207263-0c4a-4127-a6fe-38ea8c8cd1a7",
                    "adminConsentDisplayName": "Access Azure Search OpenAI Chat API",
                    "adminConsentDescription": "Allows the app to access Azure Search OpenAI Chat API as the signed-in user.",
                    "userConsentDisplayName": "Access Azure Search OpenAI Chat API",
                    "userConsentDescription": "Allow the app to access Azure Search OpenAI Chat API on your behalf",
                    "isEnabled": True,
                    "value": "access_as_user",
                    "type": "User",
                }
            ],
            # Required to match v2.0 OpenID configuration for token validation
            # Learn more at https://learn.microsoft.com/entra/identity-platform/v2-protocols-oidc#find-your-apps-openid-configuration-document-uri
            "requestedAccessTokenVersion": 2,
        },
        "requiredResourceAccess": [
            {
                "resourceAppId": "00000003-0000-0000-c000-000000000000",
                "resourceAccess": [
                    # Graph User.Read
                    {"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"},
                    # Graph email
                    {"id": "64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0", "type": "Scope"},
                    # Graph offline_access
                    {"id": "7427e0e9-2fba-42fe-b0c0-848c9e6a8182", "type": "Scope"},
                    # Graph openid
                    {"id": "37f7f235-527c-4136-accd-4a02d197296e", "type": "Scope"},
                    # Graph profile
                    {"id": "14dad69e-099b-42c9-810b-d002981feec1", "type": "Scope"},
                ],
            },
        ],
        "identifierUris": [f"api://{server_app_id}"],
    }


def create_client_app_payload(server_app_id: str, server_app_permission_setup_payload: Dict[str, Any], identifier: int):
    return {
        "displayName": f"Azure Search OpenAI Chat Client App {identifier}",
        "signInAudience": "AzureADMyOrg",
        "web": {
            "redirectUris": ["http://localhost:50505/.auth/login/aad/callback"],
            "implicitGrantSettings": {"enableIdTokenIssuance": True},
        },
        "spa": {"redirectUris": ["http://localhost:50505/redirect"]},
        "requiredResourceAccess": [
            # access_as_user from server app
            {
                "resourceAppId": server_app_id,
                "resourceAccess": [
                    {
                        "id": server_app_permission_setup_payload["api"]["oauth2PermissionScopes"][0]["id"],
                        "type": "Scope",
                    }
                ],
            },
            # Graph User.Read
            {
                "resourceAppId": "00000003-0000-0000-c000-000000000000",
                "resourceAccess": [{"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"}],
            },
        ],
    }


def create_server_app_known_client_application_payload(client_app_id: str):
    return {
        "api": {
            "knownClientApplications": [client_app_id],
        }
    }


async def main():
    if not test_authentication_enabled():
        print("Not setting up authentication.")
        exit(0)

    print("Setting up authentication...")
    credential = AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_AUTH_TENANT_ID", os.getenv("AZURE_TENANT_ID")))
    auth_headers = await get_auth_headers(credential)

    app_identifier = random_app_identifier()
    server_object_id, server_app_id, _ = await create_or_update_application_with_secret(
        auth_headers,
        app_id_env_var="AZURE_SERVER_APP_ID",
        app_secret_env_var="AZURE_SERVER_APP_SECRET",
        app_payload=create_server_app_initial_payload(app_identifier),
    )
    print("Setting up server application permissions...")
    server_app_permission_payload = create_server_app_permission_setup_payload(server_app_id)
    await update_application(auth_headers, object_id=server_object_id, app_payload=server_app_permission_payload)
    _, client_app_id, _ = await create_or_update_application_with_secret(
        auth_headers,
        app_id_env_var="AZURE_CLIENT_APP_ID",
        app_secret_env_var="AZURE_CLIENT_APP_SECRET",
        app_payload=create_client_app_payload(server_app_id, server_app_permission_payload, app_identifier),
    )
    print("Setting up server known client applications...")
    await update_application(
        auth_headers,
        object_id=server_object_id,
        app_payload=create_server_app_known_client_application_payload(client_app_id),
    )
    print("Authentication setup complete.")


if __name__ == "__main__":
    asyncio.run(main())
