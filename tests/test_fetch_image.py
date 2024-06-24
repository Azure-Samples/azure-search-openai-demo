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

from approaches.approach import Document
from core.imageshelper import fetch_image

from .mocks import MockAzureCredential


@pytest.mark.asyncio
async def test_content_file(monkeypatch, mock_env, mock_acs_search):
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
    blob_container_client = blob_client.get_container_client(os.environ["AZURE_STORAGE_CONTAINER"])

    test_document = Document(
        id="test",
        content="test content",
        embedding=[1, 2, 3],
        image_embedding=[4, 5, 6],
        oids=[],
        groups=[],
        captions=[],
        category="",
        sourcefile="test.pdf",
        sourcepage="test.pdf#page2",
    )
    image_url = await fetch_image(blob_container_client, test_document)
    assert image_url is not None
    assert image_url["url"] == "data:image/png;base64,dGVzdCBjb250ZW50"
    assert image_url["detail"] == "auto"

    test_document.sourcepage = "notfound.pdf"
    image_url = await fetch_image(blob_container_client, test_document)
    assert image_url is None

    test_document.sourcepage = ""
    image_url = await fetch_image(blob_container_client, test_document)
    assert image_url is None
