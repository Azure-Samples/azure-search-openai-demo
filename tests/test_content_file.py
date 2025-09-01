import os

import azure.storage.blob.aio
import azure.storage.filedatalake.aio
import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.core.pipeline.transport import (
    AioHttpTransportResponse,
    AsyncHttpTransport,
    HttpRequest,
)
from azure.storage.blob.aio import BlobServiceClient

import app

from .mocks import (
    MockAiohttpClientResponse,
    MockAiohttpClientResponse404,
    MockAzureCredential,
    MockBlob,
)


@pytest.mark.asyncio
async def test_content_file(monkeypatch, mock_env, mock_acs_search, mock_blob_container_client_exists):

    class MockTransport(AsyncHttpTransport):
        async def send(self, request: HttpRequest, **kwargs) -> AioHttpTransportResponse:
            if request.url.endswith("notfound.pdf") or request.url.endswith("userdoc.pdf"):
                raise ResourceNotFoundError(MockAiohttpClientResponse404(request.url, b""))
            else:
                return AioHttpTransportResponse(
                    request,
                    MockAiohttpClientResponse(
                        request.url,
                        b"test content",
                        {
                            "Content-Type": "application/octet-stream",
                            "Content-Range": "bytes 0-27/28",
                            "Content-Length": "28",
                        },
                    ),
                )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def open(self):
            pass

        async def close(self):
            pass

    mock_blob_service_client = BlobServiceClient(
        f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        transport=MockTransport(),
        retry_total=0,  # Necessary to avoid unnecessary network requests during tests
    )

    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        test_app.app.config[app.CONFIG_GLOBAL_BLOB_MANAGER].blob_service_client = mock_blob_service_client

        client = test_app.test_client()
        response = await client.get("/content/notfound.pdf")
        assert response.status_code == 404

        response = await client.get("/content/role_library.pdf")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/pdf"
        assert await response.get_data() == b"test content"

        response = await client.get("/content/role_library.pdf#page=10")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/pdf"
        assert await response.get_data() == b"test content"


@pytest.mark.asyncio
async def test_content_file_useruploaded_found(
    monkeypatch, auth_client, mock_blob_container_client, mock_blob_container_client_exists
):
    # We need to mock our the global blob and container client since the /content path checks that first!
    class MockBlobClient:
        async def download_blob(self):
            raise ResourceNotFoundError(MockAiohttpClientResponse404("userdoc.pdf", b""))

    monkeypatch.setattr(
        azure.storage.blob.aio.ContainerClient, "get_blob_client", lambda *args, **kwargs: MockBlobClient()
    )

    # Track downloaded files
    downloaded_files = []

    # Mock directory client for _ensure_directory method
    class MockDirectoryClient:
        async def get_directory_properties(self):
            # Return dummy properties to indicate directory exists
            return {"name": "test-directory"}

        async def get_access_control(self):
            # Return a dictionary with the owner matching the auth_client's user_oid
            return {"owner": "OID_X"}  # This should match the user_oid in auth_client

        def get_file_client(self, filename):
            # Return a file client for the given filename
            return MockFileClient(filename)

    class MockFileClient:
        def __init__(self, path_name):
            self.path_name = path_name

        async def download_file(self):
            downloaded_files.append(self.path_name)
            return MockBlob()

    # Mock get_directory_client to return our MockDirectoryClient
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient,
        "get_directory_client",
        lambda *args, **kwargs: MockDirectoryClient(),
    )

    response = await auth_client.get("/content/userdoc.pdf", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert len(downloaded_files) == 1


@pytest.mark.asyncio
async def test_content_file_useruploaded_notfound(
    monkeypatch, auth_client, mock_blob_container_client, mock_blob_container_client_exists
):

    class MockBlobClient:
        async def download_blob(self):
            raise ResourceNotFoundError(MockAiohttpClientResponse404("userdoc.pdf", b""))

    monkeypatch.setattr(
        azure.storage.blob.aio.ContainerClient, "get_blob_client", lambda *args, **kwargs: MockBlobClient()
    )

    # Mock directory client for _ensure_directory method
    class MockDirectoryClient:
        async def get_directory_properties(self):
            # Return dummy properties to indicate directory exists
            return {"name": "test-directory"}

        async def get_access_control(self):
            # Return a dictionary with the owner matching the auth_client's user_oid
            return {"owner": "OID_X"}  # This should match the user_oid in auth_client

        def get_file_client(self, filename):
            # Return a file client for the given filename
            return MockFileClient(filename)

    class MockFileClient:
        def __init__(self, path_name):
            self.path_name = path_name

        async def download_file(self):
            # Simulate file not found error
            raise ResourceNotFoundError(MockAiohttpClientResponse404(self.path_name, b""))

    # Mock get_directory_client to return our MockDirectoryClient
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient,
        "get_directory_client",
        lambda *args, **kwargs: MockDirectoryClient(),
    )

    response = await auth_client.get("/content/userdoc.pdf", headers={"Authorization": "Bearer test"})
    assert response.status_code == 404
