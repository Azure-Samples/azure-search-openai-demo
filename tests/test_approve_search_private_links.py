import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest

from .mocks import MockAzureCredential
from scripts import approve_search_private_links
from scripts.approve_search_private_links import (
    approve_links,
    connections_to_approve,
)

STORAGE_ID = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/adls"
CU_ID = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/cu"


def connection(name: str, endpoint_name: str, status: str) -> dict[str, Any]:
    return {
        "id": f"{STORAGE_ID}/privateEndpointConnections/{name}",
        "properties": {
            "privateEndpoint": {
                "id": f"/subscriptions/x/resourceGroups/y/providers/Microsoft.Network/privateEndpoints/{endpoint_name}"
            },
            "privateLinkServiceConnectionState": {"status": status},
        },
    }


def test_connections_to_approve_selects_pending_connections_for_the_link():
    connections = [
        connection("a", "search-shared-private-link-0", "Pending"),
        connection("b", "search-shared-private-link-1", "Pending"),
        connection("c", "search-shared-private-link-0", "Approved"),
        connection("d", "app-private-endpoint", "Pending"),
    ]

    selected = connections_to_approve("search-shared-private-link-0", connections)

    assert [c["id"].split("/")[-1] for c in selected] == ["a"]


class FakeResponse:
    def __init__(self, payload: dict[str, Any] | None = None, status: int = 200):
        self.payload = payload or {}
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, connections: list[dict[str, Any]]):
        self.connections = connections
        self.puts: list[tuple[str, dict[str, Any]]] = []

    def request(self, method: str, url: str, json: dict[str, Any] | None = None):
        if method == "PUT":
            self.puts.append((url, json or {}))
            return FakeResponse()
        return FakeResponse({"value": self.connections})


@pytest.mark.asyncio
async def test_approve_links_approves_only_pending_links():
    links = [
        {
            "name": "search-shared-private-link-0",
            "properties": {"status": "Pending", "privateLinkResourceId": STORAGE_ID},
        },
        {
            "name": "search-shared-private-link-1",
            "properties": {"status": "Approved", "privateLinkResourceId": STORAGE_ID},
        },
    ]
    session = FakeSession([connection("a", "search-shared-private-link-0", "Pending")])

    await approve_links(session, links)  # type: ignore[arg-type]

    assert len(session.puts) == 1
    url, body = session.puts[0]
    assert url == f"https://management.azure.com{STORAGE_ID}/privateEndpointConnections/a?api-version=2025-06-01"
    assert body["properties"]["privateLinkServiceConnectionState"]["status"] == "Approved"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "env",
    [
        {"AZURE_USE_PRIVATE_ENDPOINT": "false", "USE_CLOUD_INGESTION": "true", "USE_CLOUD_INGESTION_BUILTIN": "true"},
        {"AZURE_USE_PRIVATE_ENDPOINT": "true", "USE_CLOUD_INGESTION": "true", "USE_CLOUD_INGESTION_BUILTIN": "false"},
    ],
)
async def test_main_skips_without_private_builtin_ingestion(monkeypatch, env):
    monkeypatch.setattr(approve_search_private_links, "load_azd_env", lambda **kwargs: None)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    def fail(*args, **kwargs):
        raise AssertionError("should not connect to Azure")

    monkeypatch.setattr(approve_search_private_links, "AzureDeveloperCliCredential", fail)

    await approve_search_private_links.main()


class FakeLinkSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def __init__(self, statuses: list[list[str]]):
        self.statuses = statuses

    def request(self, method: str, url: str):
        statuses = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return FakeResponse(
            {
                "value": [
                    {
                        "name": f"link-{i}",
                        "properties": {
                            "status": "Pending" if s == "Failed" else s,
                            "provisioningState": "Failed" if s == "Failed" else "Succeeded",
                        },
                    }
                    for i, s in enumerate(statuses)
                ]
            }
        )


@pytest.mark.asyncio
async def test_wait_for_approval_returns_once_all_links_are_approved(monkeypatch, caplog):
    monkeypatch.setattr(approve_search_private_links.asyncio, "sleep", AsyncMock())
    session = FakeLinkSession([["Pending", "Approved"], ["Approved", "Approved"]])

    with caplog.at_level(logging.INFO, logger="scripts"):
        await approve_search_private_links.wait_for_approval(session, "/search")  # type: ignore[arg-type]

    assert "All 2 shared private links are approved" in caplog.text


@pytest.mark.asyncio
async def test_wait_for_approval_warns_on_timeout(monkeypatch, caplog):
    monkeypatch.setattr(approve_search_private_links.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(approve_search_private_links, "APPROVAL_TIMEOUT_SECONDS", 30)
    session = FakeLinkSession([["Pending"]])

    with caplog.at_level(logging.WARNING, logger="scripts"):
        await approve_search_private_links.wait_for_approval(session, "/search")  # type: ignore[arg-type]

    assert "still not approved" in caplog.text and "link-0" in caplog.text


@pytest.mark.asyncio
async def test_main_approves_links_for_the_search_service(monkeypatch):
    monkeypatch.setattr(approve_search_private_links, "load_azd_env", lambda **kwargs: None)
    for key, value in {
        "AZURE_USE_PRIVATE_ENDPOINT": "true",
        "USE_CLOUD_INGESTION": "true",
        "USE_CLOUD_INGESTION_BUILTIN": "true",
        "AZURE_SUBSCRIPTION_ID": "sub",
        "AZURE_SEARCH_SERVICE_RESOURCE_GROUP": "rg",
        "AZURE_SEARCH_SERVICE": "search",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        approve_search_private_links, "AzureDeveloperCliCredential", lambda **kwargs: MockAzureCredential()
    )
    monkeypatch.setattr(
        approve_search_private_links.aiohttp, "ClientSession", lambda **kwargs: FakeLinkSession([["Pending"]])
    )
    approve = AsyncMock()
    wait = AsyncMock()
    monkeypatch.setattr(approve_search_private_links, "approve_links", approve)
    monkeypatch.setattr(approve_search_private_links, "wait_for_approval", wait)

    await approve_search_private_links.main()

    links = approve.await_args.args[1]
    assert [link["name"] for link in links] == ["link-0"]
    assert (
        wait.await_args.args[1]
        == "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Search/searchServices/search"
    )


@pytest.mark.asyncio
async def test_wait_for_approval_reports_failed_links(caplog):
    session = FakeLinkSession([["Approved", "Failed"]])

    with caplog.at_level(logging.ERROR, logger="scripts"):
        await approve_search_private_links.wait_for_approval(session, "/search")  # type: ignore[arg-type]

    assert "failed to provision: link-1" in caplog.text


class FlakySession:
    def __init__(self):
        self.calls = 0

    def request(self, method: str, url: str):
        self.calls += 1
        return FakeResponse({"value": []}, status=504 if self.calls == 1 else 200)


@pytest.mark.asyncio
async def test_arm_request_retries_server_errors(monkeypatch):
    monkeypatch.setattr(approve_search_private_links.asyncio, "sleep", AsyncMock())
    session = FlakySession()

    result = await approve_search_private_links.arm_request(session, "GET", "/links")  # type: ignore[arg-type]

    assert result == {"value": []}
    assert session.calls == 2
