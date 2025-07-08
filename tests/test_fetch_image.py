import os

import aiohttp
import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.core.pipeline.transport import (
    AioHttpTransportResponse,
    AsyncHttpTransport,
    HttpRequest,
)
from azure.storage.blob.aio import BlobServiceClient

from .mocks import MockAzureCredential


@pytest.mark.asyncio
async def test_content_file(monkeypatch, mock_env, mock_acs_search, chat_approach):
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

    class MockTransport(AsyncHttpTransport):
        async def send(self, request: HttpRequest, **kwargs) -> AioHttpTransportResponse:
            if request.url.endswith("notfound.png"):
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

    # Then we can plug this into any SDK via kwargs:
    blob_client = BlobServiceClient(
        f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        transport=MockTransport(),
        retry_total=0,  # Necessary to avoid unnecessary network requests during tests
    )

    # Set up the BlobManager to use our mock blob client
    monkeypatch.setattr("prepdocslib.blobmanager.BlobManager._get_service_client", lambda self: blob_client)

    async def mock_exists(*args, **kwargs):
        return True

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

    blob_url = "https://sticygqdubf4x6w.blob.core.windows.net/images/Financial%20Market%20Analysis%20Report%202023.pdf/page7/figure8_1.png"
    image_url = await chat_approach.download_blob_as_base64(blob_url)
    assert image_url == "data:image/png;base64,dGVzdCBjb250ZW50"

    image_url = await chat_approach.download_blob_as_base64("notfound.png")
    assert image_url is None

    image_url = await chat_approach.download_blob_as_base64("")
    assert image_url is None
