import copy
import json

import pytest
from azure.cosmos.aio import ContainerProxy

from .mocks import MockAsyncPageIterator

for_sessions_query = [
    [
        {
            "id": "123",
            "session_id": "123",
            "entra_oid": "OID_X",
            "title": "This is a test message",
            "timestamp": 123456789,
            "type": "session",
        }
    ]
]

for_deletion_query = [
    [
        {
            "id": "123",
            "session_id": "123",
            "entra_oid": "OID_X",
            "title": "This is a test message",
            "timestamp": 123456789,
            "type": "session",
        },
        {
            "id": "123-0",
            "version": "cosmosdb-v2",
            "session_id": "123",
            "entra_oid": "OID_X",
            "type": "message_pair",
            "question": "What does a Product Manager do?",
            "response": {
                "delta": {"role": "assistant"},
                "session_state": "143c0240-b2ee-4090-8e90-2a1c58124894",
                "message": {
                    "content": "A Product Manager is responsible for leading the product management team and providing guidance on product strategy, design, development, and launch. They collaborate with internal teams and external partners to ensure successful product execution. They also develop and implement product life-cycle management processes, monitor industry trends, develop product marketing plans, research customer needs, collaborate with internal teams, develop pricing strategies, oversee product portfolio, analyze product performance, and identify areas for improvement [role_library.pdf#page=29][role_library.pdf#page=12][role_library.pdf#page=23].",
                    "role": "assistant",
                },
            },
            "order": 0,
            "timestamp": None,
        },
    ]
]

for_message_pairs_query = [
    [
        {
            "id": "123-0",
            "version": "cosmosdb-v2",
            "session_id": "123",
            "entra_oid": "OID_X",
            "type": "message_pair",
            "question": "What does a Product Manager do?",
            "response": {
                "delta": {"role": "assistant"},
                "session_state": "143c0240-b2ee-4090-8e90-2a1c58124894",
                "message": {
                    "content": "A Product Manager is responsible for leading the product management team and providing guidance on product strategy, design, development, and launch. They collaborate with internal teams and external partners to ensure successful product execution. They also develop and implement product life-cycle management processes, monitor industry trends, develop product marketing plans, research customer needs, collaborate with internal teams, develop pricing strategies, oversee product portfolio, analyze product performance, and identify areas for improvement [role_library.pdf#page=29][role_library.pdf#page=12][role_library.pdf#page=23].",
                    "role": "assistant",
                },
            },
            "order": 0,
            "timestamp": None,
        },
    ]
]


class MockCosmosDBResultsIterator:
    def __init__(self, data=[]):
        self.data = copy.deepcopy(data)

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

    async def mock_execute_item_batch(container_proxy, **kwargs):
        partition_key = kwargs["partition_key"]
        assert partition_key == ["OID_X", "123"]
        operations = kwargs["batch_operations"]
        assert len(operations) == 2
        assert operations[0][0] == "upsert"
        assert operations[1][0] == "upsert"
        session = operations[0][1][0]
        assert session["id"] == "123"
        assert session["session_id"] == "123"
        assert session["entra_oid"] == "OID_X"
        assert session["title"] == "This is a test message"
        message = operations[1][1][0]
        assert message["id"] == "123-0"
        assert message["session_id"] == "123"
        assert message["entra_oid"] == "OID_X"
        assert message["question"] == "This is a test message"
        assert message["response"] == "This is a test answer"

    monkeypatch.setattr(ContainerProxy, "execute_item_batch", mock_execute_item_batch)

    response = await auth_public_documents_client.post(
        "/chat_history",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "id": "123",
            "answers": [["This is a test message", "This is a test answer"]],
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
        "error": "The app encountered an error processing your request.\nIf you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.\nError type: <class 'IndexError'>\n"
    }


@pytest.mark.asyncio
async def test_chathistory_query(auth_public_documents_client, monkeypatch, snapshot):

    def mock_query_items(container_proxy, query, **kwargs):
        return MockCosmosDBResultsIterator(for_sessions_query)

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.get(
        "/chat_history/sessions?count=20", headers={"Authorization": "Bearer MockToken"}
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chathistory_query_continuation(auth_public_documents_client, monkeypatch, snapshot):

    def mock_query_items(container_proxy, query, **kwargs):
        return MockCosmosDBResultsIterator()

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.get(
        "/chat_history/sessions?count=20&continuation_token=123", headers={"Authorization": "Bearer MockToken"}
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chathistory_query_error_disabled(client, monkeypatch):

    response = await client.get("/chat_history/sessions", headers={"Authorization": "Bearer MockToken"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_query_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.get(
        "/chat_history/sessions", headers={"Authorization": "Bearer MockToken"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_query_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.get("/chat_history/sessions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_query_error_runtime(auth_public_documents_client, monkeypatch):

    def mock_query_items(container_proxy, query, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.get(
        "/chat_history/sessions?count=20", headers={"Authorization": "Bearer MockToken"}
    )
    assert response.status_code == 500
    assert (await response.get_json()) == {
        "error": "The app encountered an error processing your request.\nIf you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.\nError type: <class 'Exception'>\n"
    }


# Tests for getting an individual chat history item
@pytest.mark.asyncio
async def test_chathistory_getitem(auth_public_documents_client, monkeypatch, snapshot):

    def mock_query_items(container_proxy, query, **kwargs):
        return MockCosmosDBResultsIterator(for_message_pairs_query)

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    response = await auth_public_documents_client.get(
        "/chat_history/sessions/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


# Error handling tests for getting an individual chat history item
@pytest.mark.asyncio
async def test_chathistory_getitem_error_disabled(client, monkeypatch):

    response = await client.get(
        "/chat_history/sessions/123",
        headers={"Authorization": "BearerMockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_getitem_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.get(
        "/chat_history/sessions/123",
        headers={"Authorization": "BearerMockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_getitem_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.get(
        "/chat_history/sessions/123",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_getitem_error_runtime(auth_public_documents_client, monkeypatch):

    async def mock_read_item(container_proxy, item, partition_key, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "read_item", mock_read_item)

    response = await auth_public_documents_client.get(
        "/chat_history/sessions/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 500


# Tests for deleting an individual chat history item
@pytest.mark.asyncio
async def test_chathistory_deleteitem(auth_public_documents_client, monkeypatch):

    def mock_query_items(container_proxy, query, **kwargs):
        return MockCosmosDBResultsIterator(for_deletion_query)

    monkeypatch.setattr(ContainerProxy, "query_items", mock_query_items)

    # mock the batch delete operation
    async def mock_execute_item_batch(container_proxy, **kwargs):
        partition_key = kwargs["partition_key"]
        assert partition_key == ["OID_X", "123"]
        operations = kwargs["batch_operations"]
        assert len(operations) == 2
        assert operations[0][0] == "delete"
        assert operations[1][0] == "delete"
        assert operations[0][1][0] == "123"
        assert operations[1][1][0] == "123-0"

    monkeypatch.setattr(ContainerProxy, "execute_item_batch", mock_execute_item_batch)

    response = await auth_public_documents_client.delete(
        "/chat_history/sessions/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_disabled(client, monkeypatch):

    response = await client.delete(
        "/chat_history/sessions/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_container(auth_public_documents_client, monkeypatch):
    auth_public_documents_client.app.config["cosmos_history_container"] = None
    response = await auth_public_documents_client.delete(
        "/chat_history/sessions/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_entra(auth_public_documents_client, monkeypatch):
    response = await auth_public_documents_client.delete(
        "/chat_history/sessions/123",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chathistory_deleteitem_error_runtime(auth_public_documents_client, monkeypatch):

    async def mock_delete_item(container_proxy, item, partition_key, **kwargs):
        raise Exception("Test Exception")

    monkeypatch.setattr(ContainerProxy, "delete_item", mock_delete_item)

    response = await auth_public_documents_client.delete(
        "/chat_history/sessions/123",
        headers={"Authorization": "Bearer MockToken"},
    )
    assert response.status_code == 500
