import asyncio
import os

from azure.identity.aio import AzureDeveloperCliCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.public_client_application import PublicClientApplication
from msgraph.generated.models.spa_application import SpaApplication
from msgraph.generated.models.web_application import WebApplication

from auth_common import get_application, test_authentication_enabled


async def main():
    if not test_authentication_enabled():
        print("Not updating authentication.")
        exit(0)

    auth_tenant = os.getenv("AZURE_AUTH_TENANT_ID", os.environ["AZURE_TENANT_ID"])
    credential = AzureDeveloperCliCredential(tenant_id=auth_tenant)

    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    uri = os.getenv("BACKEND_URI")
    client_app_id = os.getenv("AZURE_CLIENT_APP_ID", None)
    if client_app_id:
        client_object_id = await get_application(graph_client, client_app_id)
        if client_object_id:
            print(f"Updating redirect URIs for client app ID {client_app_id}...")
            # Redirect URIs need to be relative to the deployed application
            app = Application(
                public_client=PublicClientApplication(redirect_uris=[]),
                spa=SpaApplication(
                    redirect_uris=[
                        "http://localhost:50505/redirect",
                        "http://localhost:5173/redirect",
                        f"{uri}/redirect",
                    ]
                ),
                web=WebApplication(
                    redirect_uris=[
                        f"{uri}/.auth/login/aad/callback",
                    ]
                ),
            )
            await graph_client.applications.by_application_id(client_object_id).patch(app)
            print(f"Application update for client app id {client_app_id} complete.")


if __name__ == "__main__":
    asyncio.run(main())
