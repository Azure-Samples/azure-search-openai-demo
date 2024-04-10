import asyncio
import datetime
import os
import random
import subprocess
from typing import Tuple

from azure.identity.aio import AzureDeveloperCliCredential
from msgraph import GraphServiceClient
from msgraph.generated.applications.item.add_password.add_password_post_request_body import (
    AddPasswordPostRequestBody,
)
from msgraph.generated.models.api_application import ApiApplication
from msgraph.generated.models.application import Application
from msgraph.generated.models.implicit_grant_settings import ImplicitGrantSettings
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.permission_scope import PermissionScope
from msgraph.generated.models.required_resource_access import RequiredResourceAccess
from msgraph.generated.models.resource_access import ResourceAccess
from msgraph.generated.models.service_principal import ServicePrincipal
from msgraph.generated.models.spa_application import SpaApplication
from msgraph.generated.models.web_application import WebApplication

from auth_common import get_application, test_authentication_enabled


async def create_application(graph_client: GraphServiceClient, request_app: Application) -> Tuple[str, str]:
    app = await graph_client.applications.post(request_app)
    object_id = app.id
    client_id = app.app_id

    # Create a service principal
    request_principal = ServicePrincipal(app_id=client_id, display_name=app.display_name)
    await graph_client.service_principals.post(request_principal)
    return object_id, client_id


async def add_client_secret(graph_client: GraphServiceClient, app_id: str) -> str:
    request_password = AddPasswordPostRequestBody(
        password_credential=PasswordCredential(display_name="WebAppSecret"),
    )
    result = await graph_client.applications.by_application_id(app_id).add_password.post(request_password)
    return result.secret_text


async def create_or_update_application_with_secret(
    graph_client: GraphServiceClient, app_id_env_var: str, app_secret_env_var: str, request_app: Application
) -> Tuple[str, str, bool]:
    app_id = os.getenv(app_id_env_var, "no-id")
    created_app = False
    object_id = None
    if app_id != "no-id":
        print(f"Checking if application {app_id} exists")
        object_id = await get_application(graph_client, app_id)

    if object_id:
        print("Application already exists, not creating new one")
        await graph_client.applications.by_application_id(object_id).patch(request_app)
    else:
        print("Creating application registration")
        object_id, app_id = await create_application(graph_client, request_app)
        update_azd_env(app_id_env_var, app_id)
        created_app = True

    if object_id and os.getenv(app_secret_env_var, "no-secret") == "no-secret":
        print(f"Adding client secret to {app_id}")
        client_secret = await add_client_secret(graph_client, object_id)
        update_azd_env(app_secret_env_var, client_secret)

    return (object_id, app_id, created_app)


def update_azd_env(name, val):
    subprocess.run(f"azd env set {name} {val}", shell=True)


def random_app_identifier():
    rand = random.Random()
    rand.seed(datetime.datetime.now().timestamp())
    return rand.randint(1000, 100000)


def server_app_initial(identifier: int) -> Application:
    return Application(
        display_name=f"Azure Search OpenAI Chat Server App {identifier}",
        sign_in_audience="AzureADMyOrg",
    )


def server_app_permission_setup(server_app_id: str) -> Application:
    return Application(
        api=ApiApplication(
            known_client_applications=[],
            oauth2_permission_scopes=[
                PermissionScope(
                    id="7b207263-0c4a-4127-a6fe-38ea8c8cd1a7",
                    admin_consent_display_name="Access Azure Search OpenAI Chat API",
                    admin_consent_description="Allows the app to access Azure Search OpenAI Chat API as the signed-in user.",
                    user_consent_display_name="Access Azure Search OpenAI Chat API",
                    user_consent_description="Allow the app to access Azure Search OpenAI Chat API on your behalf",
                    is_enabled=True,
                    value="access_as_user",
                    type="User",
                )
            ],
            requested_access_token_version=2,
        ),
        required_resource_access=[
            RequiredResourceAccess(
                resource_app_id="00000003-0000-0000-c000-000000000000",
                resource_access=[
                    # Graph User.Read
                    ResourceAccess(id="e1fe6dd8-ba31-4d61-89e7-88639da4683d", type="Scope"),
                    # Graph email
                    ResourceAccess(id="64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0", type="Scope"),
                    # Graph offline_access
                    ResourceAccess(id="7427e0e9-2fba-42fe-b0c0-848c9e6a8182", type="Scope"),
                    # Graph openid
                    ResourceAccess(id="37f7f235-527c-4136-accd-4a02d197296e", type="Scope"),
                    # Graph profile
                    ResourceAccess(id="14dad69e-099b-42c9-810b-d002981feec1", type="Scope"),
                ],
            )
        ],
        identifier_uris=[f"api://{server_app_id}"],
    )


def client_app(server_app_id: str, server_app: Application, identifier: int) -> Application:
    return Application(
        display_name=f"Azure Search OpenAI Chat Client App {identifier}",
        sign_in_audience="AzureADMyOrg",
        web=WebApplication(
            redirect_uris=["http://localhost:50505/.auth/login/aad/callback"],
            implicit_grant_settings=ImplicitGrantSettings(enable_id_token_issuance=True),
        ),
        spa=SpaApplication(redirect_uris=["http://localhost:50505/redirect", "http://localhost:5173/redirect"]),
        required_resource_access=[
            RequiredResourceAccess(
                resource_app_id=server_app_id,
                resource_access=[
                    ResourceAccess(
                        id=server_app.api.oauth2_permission_scopes[0].id,
                        type="Scope",
                    )
                ],
            ),
            # Graph User.Read
            RequiredResourceAccess(
                resource_app_id="00000003-0000-0000-c000-000000000000",
                resource_access=[
                    ResourceAccess(id="e1fe6dd8-ba31-4d61-89e7-88639da4683d", type="Scope"),
                ],
            ),
        ],
    )


def server_app_known_client_application(client_app_id: str) -> Application:
    return Application(
        api=ApiApplication(
            known_client_applications=[client_app_id],
        )
    )


async def main():
    if not test_authentication_enabled():
        print("Not setting up authentication.")
        exit(0)

    print("Setting up authentication...")
    credential = AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_AUTH_TENANT_ID", os.environ["AZURE_TENANT_ID"]))

    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    app_identifier = random_app_identifier()
    server_object_id, server_app_id, _ = await create_or_update_application_with_secret(
        graph_client,
        app_id_env_var="AZURE_SERVER_APP_ID",
        app_secret_env_var="AZURE_SERVER_APP_SECRET",
        request_app=server_app_initial(app_identifier),
    )
    print("Setting up server application permissions...")
    server_app_permission = server_app_permission_setup(server_app_id)
    await graph_client.applications.by_application_id(server_object_id).patch(server_app_permission)

    _, client_app_id, _ = await create_or_update_application_with_secret(
        graph_client,
        app_id_env_var="AZURE_CLIENT_APP_ID",
        app_secret_env_var="AZURE_CLIENT_APP_SECRET",
        request_app=client_app(server_app_id, server_app_permission, app_identifier),
    )

    print("Setting up server known client applications...")
    await graph_client.applications.by_application_id(server_object_id).patch(
        server_app_known_client_application(client_app_id)
    )
    print("Authentication setup complete.")


if __name__ == "__main__":
    asyncio.run(main())
