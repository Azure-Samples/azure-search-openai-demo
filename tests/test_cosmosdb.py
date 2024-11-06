import pytest
from azure.cosmos.aio import ContainerProxy


@pytest.mark.asyncio
async def test_chathistory(auth_public_documents_client, monkeypatch):

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
