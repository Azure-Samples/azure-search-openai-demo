import os

import aiohttp
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

from .mocks import MockAzureCredential, MockBlob


class MockAiohttpClientResponse404(aiohttp.ClientResponse):
    def __init__(self, url, body_bytes, headers=None):
        self._body = body_bytes
        self._headers = headers
        self._cache = {}
        self.status = 404
        self.reason = "Not Found"
        self._url = url


class MockAiohttpClientResponse(aiohttp.ClientResponse):
    def __init__(self, url, body_bytes, headers=None):
        self._body = body_bytes
        self._headers = headers
        self._cache = {}
        self.status = 200
        self.reason = "OK"
        self._url = url


@pytest.mark.asyncio
async def test_content_file(monkeypatch, mock_env, mock_acs_search):

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

    blob_client = BlobServiceClient(
        f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        transport=MockTransport(),
        retry_total=0,  # Necessary to avoid unnecessary network requests during tests
    )
    blob_container_client = blob_client.get_container_client(os.environ["AZURE_STORAGE_CONTAINER"])

    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        quart_app.config.update({"blob_container_client": blob_container_client})

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
async def test_content_file_useruploaded_found(monkeypatch, auth_client, mock_blob_container_client):

    class MockBlobClient:
        async def download_blob(self):
            raise ResourceNotFoundError(MockAiohttpClientResponse404("userdoc.pdf", b""))

    monkeypatch.setattr(
        azure.storage.blob.aio.ContainerClient, "get_blob_client", lambda *args, **kwargs: MockBlobClient()
    )

    downloaded_files = []

    async def mock_download_file(self):
        downloaded_files.append(self.path_name)
        return MockBlob()

    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "download_file", mock_download_file)

    response = await auth_client.get("/content/userdoc.pdf", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert len(downloaded_files) == 1


@pytest.mark.asyncio
async def test_content_file_useruploaded_notfound(monkeypatch, auth_client, mock_blob_container_client):

    class MockBlobClient:
        async def download_blob(self):
            raise ResourceNotFoundError(MockAiohttpClientResponse404("userdoc.pdf", b""))

    monkeypatch.setattr(
        azure.storage.blob.aio.ContainerClient, "get_blob_client", lambda *args, **kwargs: MockBlobClient()
    )

    async def mock_download_file(self):
        raise ResourceNotFoundError(MockAiohttpClientResponse404("userdoc.pdf", b""))

    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "download_file", mock_download_file)

    response = await auth_client.get("/content/userdoc.pdf", headers={"Authorization": "Bearer test"})
    assert response.status_code == 404
