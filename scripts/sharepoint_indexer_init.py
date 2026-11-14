"""Creates the Entra app registration that the SharePoint indexer uses for cloud ingestion.

Runs in the preprovision hook when USE_CLOUD_INGESTION_SHAREPOINT is true. Like auth_init.py,
it creates the app (or updates an existing one from the azd env) with a client secret, and
stores both in the azd env, where setup_cloud_ingestion.py reads them.
"""

import asyncio
import os
import uuid

from azure.identity.aio import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from kiota_abstractions.api_error import APIError
from msgraph import GraphServiceClient
from msgraph.generated.models.app_role_assignment import AppRoleAssignment
from msgraph.generated.models.application import Application
from msgraph.generated.models.required_resource_access import RequiredResourceAccess
from msgraph.generated.models.resource_access import ResourceAccess

from auth_init import create_or_update_application_with_secret, random_app_identifier

GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
# Application permissions the SharePoint indexer needs to read document libraries
INDEXER_GRAPH_PERMISSIONS = ["Files.Read.All", "Sites.Read.All"]


def sharepoint_indexer_app(identifier: int, graph_role_ids: dict[str, str]) -> Application:
    return Application(
        display_name=f"Azure Search OpenAI Chat SharePoint Indexer {identifier}",
        sign_in_audience="AzureADMyOrg",
        required_resource_access=[
            RequiredResourceAccess(
                resource_app_id=GRAPH_APP_ID,
                resource_access=[
                    ResourceAccess(id=uuid.UUID(graph_role_ids[permission]), type="Role")
                    for permission in INDEXER_GRAPH_PERMISSIONS
                ],
            )
        ],
    )


async def get_graph_role_ids(graph_client: GraphServiceClient) -> tuple[str, dict[str, str]]:
    """Returns the Microsoft Graph service principal ID and the IDs of the required app roles."""
    graph_principal = await graph_client.service_principals_with_app_id(GRAPH_APP_ID).get()
    if graph_principal is None or graph_principal.id is None:
        raise ValueError("Unable to locate the Microsoft Graph service principal")
    role_ids = {
        role.value: str(role.id)
        for role in graph_principal.app_roles or []
        if role.value in INDEXER_GRAPH_PERMISSIONS and role.id is not None
    }
    missing = set(INDEXER_GRAPH_PERMISSIONS) - set(role_ids)
    if missing:
        raise ValueError(f"Microsoft Graph app roles not found: {', '.join(sorted(missing))}")
    return graph_principal.id, role_ids


async def grant_application_permissions(
    graph_client: GraphServiceClient, app_id: str, graph_principal_id: str, graph_role_ids: dict[str, str]
) -> bool:
    """Grants admin consent for the app's Graph application permissions. Returns False if not allowed."""
    app_principal = await graph_client.service_principals_with_app_id(app_id).get()
    if app_principal is None or app_principal.id is None:
        raise ValueError("Unable to locate service principal for the SharePoint indexer application")

    existing = await graph_client.service_principals.by_service_principal_id(
        app_principal.id
    ).app_role_assignments.get()
    granted_role_ids = {str(assignment.app_role_id) for assignment in (existing.value if existing else []) or []}

    for permission in INDEXER_GRAPH_PERMISSIONS:
        role_id = graph_role_ids[permission]
        if role_id in granted_role_ids:
            print(f"Admin consent already granted for {permission}")
            continue
        try:
            await graph_client.service_principals.by_service_principal_id(graph_principal_id).app_role_assigned_to.post(
                AppRoleAssignment(
                    principal_id=uuid.UUID(app_principal.id),
                    resource_id=uuid.UUID(graph_principal_id),
                    app_role_id=uuid.UUID(role_id),
                )
            )
            print(f"Granted admin consent for {permission}")
        except APIError as error:
            if error.response_status_code in {401, 403}:
                print(f"Failed to grant admin consent for {permission}: {error.message}")
                return False
            raise
    return True


def validate_sharepoint_settings() -> list[str]:
    """Returns problems that would keep the SharePoint indexer from being set up after deployment,
    so the app registration (with tenant-wide read permissions) isn't created for nothing."""
    problems = []
    if os.getenv("USE_CLOUD_INGESTION", "").lower() != "true":
        problems.append("USE_CLOUD_INGESTION must be set to true.")
    if os.getenv("USE_CLOUD_INGESTION_BUILTIN", "").lower() != "true":
        problems.append("USE_CLOUD_INGESTION_BUILTIN must be set to true.")
    if not os.getenv("AZURE_SHAREPOINT_SITE_URL", "").strip():
        problems.append("AZURE_SHAREPOINT_SITE_URL must be set to the URL of your SharePoint site.")
    return problems


async def main():  # pragma: no cover
    load_azd_env(override=os.getenv("LOADING_MODE_FOR_AZD_ENV_VARS") != "no-override")

    if os.getenv("USE_CLOUD_INGESTION_SHAREPOINT", "").lower() != "true":
        print("USE_CLOUD_INGESTION_SHAREPOINT is not set, skipping SharePoint indexer app setup.")
        return

    problems = validate_sharepoint_settings()
    if problems:
        print("Error: USE_CLOUD_INGESTION_SHAREPOINT is set to true, but:")
        for problem in problems:
            print(f"  - {problem}")
        exit(1)

    tenant_id = (os.getenv("AZURE_SHAREPOINT_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "").strip()
    if not tenant_id:
        print("Error: Set AZURE_SHAREPOINT_TENANT_ID (or AZURE_TENANT_ID) to the tenant of your SharePoint site.")
        exit(1)
    print("Setting up the SharePoint indexer app registration in tenant", tenant_id)
    credential = AzureDeveloperCliCredential(tenant_id=tenant_id)
    graph_client = GraphServiceClient(credentials=credential, scopes=["https://graph.microsoft.com/.default"])

    graph_principal_id, graph_role_ids = await get_graph_role_ids(graph_client)
    _, app_id, _ = await create_or_update_application_with_secret(
        graph_client,
        app_id_env_var="AZURE_SHAREPOINT_INDEXER_APP_ID",
        app_secret_env_var="AZURE_SHAREPOINT_INDEXER_APP_SECRET",
        request_app=sharepoint_indexer_app(random_app_identifier(), graph_role_ids),
    )

    print("Attempting to grant admin consent for the SharePoint indexer application...")
    if not await grant_application_permissions(graph_client, app_id, graph_principal_id, graph_role_ids):
        print(
            "Ask a Privileged Role Administrator or Global Administrator to grant admin consent for "
            f"{', '.join(INDEXER_GRAPH_PERMISSIONS)} to application {app_id}, either in the Azure portal "
            f"(App registrations > API permissions > Grant admin consent) or with:\n"
            f"  az ad app permission admin-consent --id {app_id}"
        )

    print("SharePoint indexer app setup complete.")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
