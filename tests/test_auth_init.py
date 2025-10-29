import json
import os
from types import SimpleNamespace
from typing import Optional
from unittest import mock

import pytest
from kiota_abstractions.api_error import APIError
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.service_principal import ServicePrincipal

from .mocks import MockAzureCredential
from scripts import auth_init
from scripts.auth_init import (
    add_client_secret,
    client_app,
    create_application,
    create_or_update_application_with_secret,
    grant_application_admin_consent,
    server_app_initial,
    server_app_permission_setup,
)

MOCK_OBJECT_ID = "OBJ123"
MOCK_APP_ID = "APP123"
MOCK_SECRET = "SECRET_VALUE"
EXISTING_MOCK_OBJECT_ID = "OBJ999"
MOCK_CLIENT_APP_ID = "client-app"
MOCK_SERVER_APP_ID = "server-app"


@pytest.fixture
def graph_client(monkeypatch):
    """GraphServiceClient whose network layer is intercepted to avoid real HTTP calls.

    We exercise real request builders while intercepting the adapter's send_async.
    """

    client = GraphServiceClient(credentials=MockAzureCredential(), scopes=["https://graph.microsoft.com/.default"])

    calls = {
        "applications.post": [],
        "applications.patch": [],
        "applications.add_password.post": [],
        "service_principals.post": [],
    }
    created_ids = {"object_id": MOCK_OBJECT_ID, "app_id": MOCK_APP_ID}
    secret_text_value = {"value": MOCK_SECRET}
    service_principals = {
        MOCK_CLIENT_APP_ID: SimpleNamespace(id="client-sp"),
        MOCK_SERVER_APP_ID: SimpleNamespace(id="server-sp"),
        "00000003-0000-0000-c000-000000000000": SimpleNamespace(id="graph-sp"),
        "880da380-985e-4198-81b9-e05b1cc53158": SimpleNamespace(id="resource-sp"),
    }

    def fake_service_principals_with_app_id(app_id):
        if app_id not in service_principals:
            raise AssertionError(f"Unexpected service principal lookup for {app_id}")
        return FakeRequestBuilder(service_principals[app_id])

    oauth_grants = FakeOAuthGrant()

    async def fake_send_async(request_info, return_type, error_mapping=None):
        url = request_info.url or ""
        method = request_info.http_method.value
        if method == "POST" and url.endswith("/applications"):
            body = request_info.content
            calls["applications.post"].append(body)
            return Application(
                id=created_ids["object_id"],
                app_id=created_ids["app_id"],
                display_name=getattr(body, "display_name", None),
            )
        if method == "POST" and url.endswith("/servicePrincipals"):
            calls["service_principals.post"].append(request_info.content)
            return ServicePrincipal()
        if method == "PATCH" and "/applications/" in url:
            calls["applications.patch"].append(request_info.content)
            return Application()
        if method == "POST" and url.endswith("/addPassword"):
            calls["applications.add_password.post"].append(request_info.content)
            return PasswordCredential(secret_text=secret_text_value["value"])
        if "oauth2PermissionGrants" in url:
            if method == "GET":
                return oauth_grants.next_response()
            if method == "POST":
                return oauth_grants.handle_post(request_info.content)
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(client, "service_principals_with_app_id", fake_service_principals_with_app_id)

    # Patch the adapter
    monkeypatch.setattr(client.request_adapter, "send_async", fake_send_async)

    client._test_calls = calls
    client._test_secret_text_value = secret_text_value
    client._test_ids = created_ids
    client._test_service_principals = service_principals
    client._test_oauth_grants = oauth_grants
    return client


class FakeRequestBuilder:
    def __init__(self, result):
        self._result = result

    async def get(self):
        return self._result


class FakeOAuthGrant:
    def __init__(self):
        self.responses: list[SimpleNamespace] = []
        self.raise_on_post: Optional[APIError] = None
        self.posted = []
        self.post_attempts = 0

    def configure(self, responses, raise_on_post=None):
        self.responses = list(responses)
        self.raise_on_post = raise_on_post
        self.posted = []
        self.post_attempts = 0

    def next_response(self):
        if not self.responses:
            raise AssertionError("No configured response for oauth2_permission_grants.get")
        return self.responses.pop(0)

    def handle_post(self, grant):
        self.post_attempts += 1
        if self.raise_on_post is not None:
            error = self.raise_on_post
            self.raise_on_post = None
            raise error
        self.posted.append(json.loads(grant.decode("utf-8")))
        return grant


@pytest.mark.asyncio
async def test_create_application_success(graph_client):
    graph = graph_client
    request = server_app_initial(42)
    object_id, app_id = await create_application(graph, request)
    assert object_id == MOCK_OBJECT_ID
    assert app_id == MOCK_APP_ID
    assert len(graph._test_calls["service_principals.post"]) == 1


@pytest.mark.asyncio
async def test_create_application_missing_ids(graph_client, monkeypatch):
    graph = graph_client

    original_send_async = graph.request_adapter.send_async

    async def bad_send_async(request_info, return_type, error_mapping=None):
        url = request_info.url or ""
        method = request_info.http_method.value
        if method == "POST" and url.endswith("/applications"):
            return Application(id=None, app_id=None)
        return await original_send_async(request_info, return_type, error_mapping)

    monkeypatch.setattr(graph.request_adapter, "send_async", bad_send_async)
    with pytest.raises(ValueError):
        await create_application(graph, server_app_initial(1))


@pytest.mark.asyncio
async def test_add_client_secret_success(graph_client):
    graph = graph_client
    secret = await add_client_secret(graph, MOCK_OBJECT_ID)
    assert secret == MOCK_SECRET
    assert len(graph._test_calls["applications.add_password.post"]) == 1


@pytest.mark.asyncio
async def test_add_client_secret_missing_secret(graph_client):
    graph = graph_client
    graph._test_secret_text_value["value"] = None
    with pytest.raises(ValueError):
        await add_client_secret(graph, MOCK_OBJECT_ID)


@pytest.mark.asyncio
async def test_create_or_update_application_creates_and_adds_secret(graph_client, monkeypatch):
    graph = graph_client
    updates: list[tuple[str, str]] = []

    def fake_update_env(name, val):
        updates.append((name, val))

    # Ensure env vars not set
    with mock.patch.dict(os.environ, {}, clear=True):
        monkeypatch.setattr(auth_init, "update_azd_env", fake_update_env)

        # Force get_application to return None (not found)
        async def fake_get_application(graph_client, client_id):
            return None

        monkeypatch.setattr("scripts.auth_init.get_application", fake_get_application)
        object_id, app_id, created = await create_or_update_application_with_secret(
            graph,
            app_id_env_var="AZURE_SERVER_APP_ID",
            app_secret_env_var="AZURE_SERVER_APP_SECRET",
            request_app=server_app_initial(55),
        )
        assert created is True
        assert object_id == MOCK_OBJECT_ID
        assert app_id == MOCK_APP_ID
        # Two updates: app id and secret
        assert {u[0] for u in updates} == {"AZURE_SERVER_APP_ID", "AZURE_SERVER_APP_SECRET"}
    assert len(graph._test_calls["applications.add_password.post"]) == 1


@pytest.mark.asyncio
async def test_create_or_update_application_existing_adds_secret(graph_client, monkeypatch):
    graph = graph_client
    updates: list[tuple[str, str]] = []

    def fake_update_env(name, val):
        updates.append((name, val))

    with mock.patch.dict(os.environ, {"AZURE_SERVER_APP_ID": MOCK_APP_ID}, clear=True):
        monkeypatch.setattr(auth_init, "update_azd_env", fake_update_env)

        async def fake_get_application(graph_client, client_id):
            return EXISTING_MOCK_OBJECT_ID

        monkeypatch.setattr("scripts.auth_init.get_application", fake_get_application)
        object_id, app_id, created = await create_or_update_application_with_secret(
            graph,
            app_id_env_var="AZURE_SERVER_APP_ID",
            app_secret_env_var="AZURE_SERVER_APP_SECRET",
            request_app=server_app_initial(77),
        )
        assert created is False
        assert object_id == EXISTING_MOCK_OBJECT_ID
        assert app_id == MOCK_APP_ID
        # Secret should be added since not in env
        assert any(name == "AZURE_SERVER_APP_SECRET" for name, _ in updates)
        # Application patch should have been called
    # Patch captured
    assert len(graph._test_calls["applications.patch"]) == 1


@pytest.mark.asyncio
async def test_create_or_update_application_existing_with_secret(graph_client, monkeypatch):
    graph = graph_client
    with mock.patch.dict(
        os.environ, {"AZURE_SERVER_APP_ID": MOCK_APP_ID, "AZURE_SERVER_APP_SECRET": "EXISTING"}, clear=True
    ):

        async def fake_get_application(graph_client, client_id):
            return EXISTING_MOCK_OBJECT_ID

        monkeypatch.setattr("scripts.auth_init.get_application", fake_get_application)
        object_id, app_id, created = await create_or_update_application_with_secret(
            graph,
            app_id_env_var="AZURE_SERVER_APP_ID",
            app_secret_env_var="AZURE_SERVER_APP_SECRET",
            request_app=server_app_initial(88),
        )
        assert created is False
        assert object_id == EXISTING_MOCK_OBJECT_ID
        assert app_id == MOCK_APP_ID
        # No secret added
    assert len(graph._test_calls["applications.add_password.post"]) == 0


def test_client_app_validation_errors():
    # Server app without api
    server_app = server_app_initial(1)
    server_app.api = None
    with pytest.raises(ValueError):
        client_app("server_app_id", server_app, 2)

    # Server app with empty scopes
    # attach empty api
    server_app_permission = server_app_permission_setup("server_app")
    server_app_permission.api.oauth2_permission_scopes = []
    with pytest.raises(ValueError):
        client_app("server_app_id", server_app_permission, 2)


def test_client_app_success():
    server_app_permission = server_app_permission_setup("server_app")
    c_app = client_app("server_app", server_app_permission, 123)
    assert c_app.web is not None
    assert c_app.spa is not None
    assert c_app.required_resource_access is not None
    assert len(c_app.required_resource_access) >= 1


def test_server_app_permission_setup():
    # simulate after creation we know app id
    app_with_permissions = server_app_permission_setup("server_app_id")
    assert app_with_permissions.identifier_uris == ["api://server_app_id"]
    assert app_with_permissions.required_resource_access is not None
    assert len(app_with_permissions.required_resource_access) == 2


@pytest.mark.asyncio
async def test_grant_application_admin_consent_creates_grants(graph_client):
    graph = graph_client
    oauth_grants = graph._test_oauth_grants
    oauth_grants.configure(responses=[SimpleNamespace(value=[]), SimpleNamespace(value=[]), SimpleNamespace(value=[])])

    await grant_application_admin_consent(graph, MOCK_CLIENT_APP_ID, MOCK_SERVER_APP_ID)

    assert oauth_grants.post_attempts == 3
    scopes = {grant["scope"] for grant in oauth_grants.posted}
    assert scopes == {
        "User.Read email offline_access openid profile",
        "user_impersonation",
        "access_as_user",
    }


@pytest.mark.asyncio
async def test_grant_application_admin_consent_skips_existing_grants(graph_client):
    graph = graph_client
    oauth_grants = graph._test_oauth_grants
    oauth_grants.configure(
        responses=[
            SimpleNamespace(value=[SimpleNamespace(id="grant1")]),
            SimpleNamespace(value=[SimpleNamespace(id="grant2")]),
            SimpleNamespace(value=[SimpleNamespace(id="grant3")]),
        ]
    )

    await grant_application_admin_consent(graph, MOCK_CLIENT_APP_ID, MOCK_SERVER_APP_ID)

    assert oauth_grants.post_attempts == 0
    assert not oauth_grants.posted


@pytest.mark.asyncio
async def test_grant_application_admin_consent_handles_insufficient_permissions(graph_client):
    graph = graph_client
    oauth_grants = graph._test_oauth_grants
    error = APIError()
    error.response_status_code = 403
    error.message = "Forbidden"
    oauth_grants.configure(responses=[SimpleNamespace(value=[])], raise_on_post=error)

    await grant_application_admin_consent(graph, MOCK_CLIENT_APP_ID, MOCK_SERVER_APP_ID)

    assert oauth_grants.post_attempts == 1
    assert not oauth_grants.posted
