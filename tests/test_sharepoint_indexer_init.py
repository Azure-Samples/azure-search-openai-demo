import json
import uuid
from types import SimpleNamespace

import pytest
from kiota_abstractions.api_error import APIError
from msgraph import GraphServiceClient

from .mocks import MockAzureCredential
from scripts.sharepoint_indexer_init import (
    get_graph_role_ids,
    grant_application_permissions,
    sharepoint_indexer_app,
    validate_sharepoint_settings,
)

GRAPH_SP_ID = str(uuid.uuid4())
INDEXER_SP_ID = str(uuid.uuid4())
INDEXER_APP_ID = "indexer-app"
ROLE_IDS = {"Files.Read.All": str(uuid.uuid4()), "Sites.Read.All": str(uuid.uuid4())}


class FakeRequestBuilder:
    def __init__(self, result):
        self.result = result

    async def get(self):
        return self.result


@pytest.fixture
def graph_client(monkeypatch):
    """GraphServiceClient with the HTTP layer intercepted, so real request builders are exercised."""
    client = GraphServiceClient(credentials=MockAzureCredential(), scopes=["https://graph.microsoft.com/.default"])
    graph_principal = SimpleNamespace(
        id=GRAPH_SP_ID,
        app_roles=[SimpleNamespace(value=name, id=uuid.UUID(role_id)) for name, role_id in ROLE_IDS.items()]
        + [SimpleNamespace(value="User.Read.All", id=uuid.uuid4())],
    )
    service_principals = {
        "00000003-0000-0000-c000-000000000000": graph_principal,
        INDEXER_APP_ID: SimpleNamespace(id=INDEXER_SP_ID),
    }
    monkeypatch.setattr(
        client, "service_principals_with_app_id", lambda app_id: FakeRequestBuilder(service_principals[app_id])
    )

    state = {"existing": [], "posted": [], "raise_on_post": None}

    async def fake_send_async(request_info, return_type, error_mapping=None):
        url = request_info.url or ""
        method = request_info.http_method.value
        if method == "GET" and url.endswith(f"/servicePrincipals/{INDEXER_SP_ID}/appRoleAssignments"):
            return SimpleNamespace(value=[SimpleNamespace(app_role_id=uuid.UUID(r)) for r in state["existing"]])
        if method == "POST" and url.endswith(f"/servicePrincipals/{GRAPH_SP_ID}/appRoleAssignedTo"):
            if state["raise_on_post"] is not None:
                raise state["raise_on_post"]
            state["posted"].append(json.loads(request_info.content.decode("utf-8")))
            return None
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(client.request_adapter, "send_async", fake_send_async)
    client._test_state = state
    client._test_graph_principal = graph_principal
    return client


def test_sharepoint_indexer_app_requests_application_permissions():
    app = sharepoint_indexer_app(1234, ROLE_IDS)

    assert app.display_name == "Azure Search OpenAI Chat SharePoint Indexer 1234"
    assert app.required_resource_access[0].resource_app_id == "00000003-0000-0000-c000-000000000000"
    accesses = app.required_resource_access[0].resource_access
    assert {str(access.id) for access in accesses} == set(ROLE_IDS.values())
    assert all(access.type == "Role" for access in accesses)


@pytest.mark.asyncio
async def test_get_graph_role_ids(graph_client):
    graph_principal_id, role_ids = await get_graph_role_ids(graph_client)

    assert graph_principal_id == GRAPH_SP_ID
    assert role_ids == ROLE_IDS


@pytest.mark.asyncio
async def test_get_graph_role_ids_missing_role(graph_client):
    graph_client._test_graph_principal.app_roles = graph_client._test_graph_principal.app_roles[1:]

    with pytest.raises(ValueError, match="Files.Read.All"):
        await get_graph_role_ids(graph_client)


@pytest.mark.asyncio
async def test_grant_application_permissions_only_grants_missing_roles(graph_client):
    graph_client._test_state["existing"] = [ROLE_IDS["Files.Read.All"]]

    granted = await grant_application_permissions(graph_client, INDEXER_APP_ID, GRAPH_SP_ID, ROLE_IDS)

    assert granted is True
    [posted] = graph_client._test_state["posted"]
    assert posted["appRoleId"] == ROLE_IDS["Sites.Read.All"]
    assert posted["principalId"] == INDEXER_SP_ID
    assert posted["resourceId"] == GRAPH_SP_ID


@pytest.mark.asyncio
async def test_grant_application_permissions_handles_insufficient_permissions(graph_client, capsys):
    error = APIError()
    error.response_status_code = 403
    error.message = "Forbidden"
    graph_client._test_state["raise_on_post"] = error

    granted = await grant_application_permissions(graph_client, INDEXER_APP_ID, GRAPH_SP_ID, ROLE_IDS)

    assert granted is False
    assert "Failed to grant admin consent for Files.Read.All: Forbidden" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_grant_application_permissions_reraises_other_errors(graph_client):
    error = APIError()
    error.response_status_code = 500
    graph_client._test_state["raise_on_post"] = error

    with pytest.raises(APIError):
        await grant_application_permissions(graph_client, INDEXER_APP_ID, GRAPH_SP_ID, ROLE_IDS)


@pytest.mark.asyncio
async def test_missing_service_principals_raise(graph_client, monkeypatch):
    monkeypatch.setattr(graph_client, "service_principals_with_app_id", lambda app_id: FakeRequestBuilder(None))

    with pytest.raises(ValueError, match="Microsoft Graph service principal"):
        await get_graph_role_ids(graph_client)
    with pytest.raises(ValueError, match="SharePoint indexer application"):
        await grant_application_permissions(graph_client, INDEXER_APP_ID, GRAPH_SP_ID, ROLE_IDS)


def test_validate_sharepoint_settings_valid(monkeypatch):
    monkeypatch.setenv("USE_CLOUD_INGESTION", "true")
    monkeypatch.setenv("USE_CLOUD_INGESTION_BUILTIN", "true")
    monkeypatch.setenv("AZURE_SHAREPOINT_SITE_URL", "https://contoso.sharepoint.com/sites/mysite")
    assert validate_sharepoint_settings() == []


def test_validate_sharepoint_settings_reports_each_missing_prerequisite(monkeypatch):
    monkeypatch.delenv("USE_CLOUD_INGESTION", raising=False)
    monkeypatch.setenv("USE_CLOUD_INGESTION_BUILTIN", "false")
    monkeypatch.setenv("AZURE_SHAREPOINT_SITE_URL", "  ")
    problems = validate_sharepoint_settings()
    assert len(problems) == 3
    assert any("USE_CLOUD_INGESTION must" in p for p in problems)
    assert any("USE_CLOUD_INGESTION_BUILTIN" in p for p in problems)
    assert any("AZURE_SHAREPOINT_SITE_URL" in p for p in problems)
