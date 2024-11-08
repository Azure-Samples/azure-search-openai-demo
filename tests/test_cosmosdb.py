import json

import pytest
from azure.cosmos.aio import ContainerProxy

from .mocks import MockAsyncPageIterator


class MockCosmosDBResultsIterator:
    def __init__(self, empty=False):
        if empty:
            self.data = []
        else:
            self.data = [
                [
                    {
                        "id": "123",
                        "entra_oid": "OID_X",
                        "title": "This is a test message",
                        "timestamp": 123456789,
                        "answers": [["This is a test message"]],
                    }
                ]
            ]

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.data:
            raise StopAsyncIteration
        return MockAsyncPageIterator(self.data.pop(0))

    async def get_count(self):
        return len(self.data)

    def by_page(self, continuation_token=None):
        if continuation_token:
            self.continuation_token = continuation_token + "next"
        else:
            self.continuation_token = "next"
        return self


@pytest.mark.asyncio
async def test_chathistory_newitem(auth_public_documents_client, monkeypatch):

    async def mock_upsert_item(container_proxy, item, **kwargs):
        assert item["id"] == "123"
        assert item["answers"] == [["This is a test message"]]
        assert item["entra_oid"] == "OID_X"
        assert item["title"] == "This is a test message"

    monkeypatch.setattr(ContainerProxy, "upsert_item", mock_upsert_item)

    response = await auth_public_documents_client.post(
        "/chat_history",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_chathistory_newitem_error_disabled(client, monkeypatch):

    response = await client.post(
        "/chat_history",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_newitem_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.post(
        "/chat_history",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_newitem_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.post(
        "/chat_history",
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_newitem_error_runtime(auth_public_documents_client, monkeypatch):

    async def mock_upsert_item(container_proxy, item, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "upsert_item", mock_upsert_item)

    response = await auth_public_documents_client.post(
        "/chat_history",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 500
    assert (await response.get_json()) == {
        "error": "The app encountered an error processing your request.\nIf you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.\nError type: <class 'Exception'>\n"
    }


@pytest.mark.asyncio
async def test_chathistory_query(auth_public_documents_client, monkeypatch, snapshot):

    def mock_query_items(container_proxy, query, **kwargs):
        return MockCosmosDBResultsIterator()

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.post(
        "/chat_history/items",
        headers={"Authorization": "Bearer MockToken"},
        json={"count": 20},
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chathistory_query_continuation(auth_public_documents_client, monkeypatch, snapshot):

    def mock_query_items(container_proxy, query, **kwargs):
        return MockCosmosDBResultsIterator(empty=True)

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.post(
        "/chat_history/items",
        headers={"Authorization": "Bearer MockToken"},
        json={"count": 20},
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chathistory_query_error_disabled(client, monkeypatch):

    response = await client.post(
        "/chat_history/items",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_query_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.post(
        "/chat_history/items",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_query_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.post(
        "/chat_history/items",
        json={
            "id": "123",
            "answers": [["This is a test message"]],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_query_error_runtime(auth_public_documents_client, monkeypatch):

    def mock_query_items(container_proxy, query, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.post(
        "/chat_history/items",
        headers={"Authorization": "Bearer MockToken"},
        json={"count": 20},
    )
    assert response.status_code == 500
    assert (await response.get_json()) == {
        "error": "The app encountered an error processing your request.\nIf you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.\nError type: <class 'Exception'>\n"
    }


# Tests for getting an individual chat history item
@pytest.mark.asyncio
async def test_chathistory_getitem(auth_public_documents_client, monkeypatch, snapshot):

    async def mock_read_item(container_proxy, item, partition_key, **kwargs):
        return {
            "id": "123",
            "entra_oid": "OID_X",
            "title": "This is a test message",
            "timestamp": 123456789,
            "answers": [["This is a test message"]],
        }

    monkeypatch.setattr(ContainerProxy, "read_item", mock_read_item)

    response = await auth_public_documents_client.get(
        "/chat_history/items/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


# Error handling tests for getting an individual chat history item
@pytest.mark.asyncio
async def test_chathistory_getitem_error_disabled(client, monkeypatch):

    response = await client.get(
        "/chat_history/items/123",
        headers={"Authorization": "BearerMockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_getitem_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.get(
        "/chat_history/items/123",
        headers={"Authorization": "BearerMockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_getitem_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.get(
        "/chat_history/items/123",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_getitem_error_runtime(auth_public_documents_client, monkeypatch):

    async def mock_read_item(container_proxy, item, partition_key, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "read_item", mock_read_item)

    response = await auth_public_documents_client.get(
        "/chat_history/items/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 500


# Tests for deleting an individual chat history item
@pytest.mark.asyncio
async def test_chathistory_deleteitem(auth_public_documents_client, monkeypatch):

    async def mock_delete_item(container_proxy, item, partition_key, **kwargs):
        assert item == "123"
        assert partition_key == "OID_X"

    monkeypatch.setattr(ContainerProxy, "delete_item", mock_delete_item)

    response = await auth_public_documents_client.delete(
        "/chat_history/items/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_disabled(client, monkeypatch):

    response = await client.delete(
        "/chat_history/items/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.delete(
        "/chat_history/items/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.delete(
        "/chat_history/items/123",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_runtime(auth_public_documents_client, monkeypatch):

    async def mock_delete_item(container_proxy, item, partition_key, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "delete_item", mock_delete_item)

    response = await auth_public_documents_client.delete(
        "/chat_history/items/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 500
