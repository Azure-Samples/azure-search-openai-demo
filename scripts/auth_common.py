import os
from typing import Optional

from kiota_abstractions.api_error import APIError
from msgraph import GraphServiceClient


async def get_application(graph_client: GraphServiceClient, client_id: str) -> Optional[str]:
    try:
        app = await graph_client.applications_with_app_id(client_id).get()
        return app.id
    except APIError:
        return None


def test_authentication_enabled():
    use_authentication = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    require_access_control = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    if require_access_control and not use_authentication:
        print("AZURE_ENFORCE_ACCESS_CONTROL is true, but AZURE_USE_AUTHENTICATION is false. Stopping...")
        return False

    if not use_authentication:
        return False

    return True
