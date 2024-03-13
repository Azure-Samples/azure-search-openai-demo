import azure.storage.filedatalake.aio
import pytest


@pytest.mark.asyncio
async def test_list_uploaded(auth_client, monkeypatch, mock_data_lake_service_client):
    response = await auth_client.get("/list_uploaded", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert (await response.get_json()) == ["a.txt", "b.txt", "c.txt"]


@pytest.mark.asyncio
async def test_delete_uploaded(auth_client, monkeypatch, mock_data_lake_service_client):
    async def mock_delete_file(self, **kwargs):
        return None

    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "delete_file", mock_delete_file)

    response = await auth_client.post(
        "/delete_uploaded", headers={"Authorization": "Bearer test"}, json={"filename": "a.txt"}
    )
    assert response.status_code == 200
