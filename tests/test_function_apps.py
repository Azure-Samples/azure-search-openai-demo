import base64
import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import azure.functions as func
import pytest

from document_extractor import function_app as document_extractor
from figure_processor import function_app as figure_processor
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SentenceTextSplitter
from tests.mocks import TEST_PNG_BYTES
from text_processor import function_app as text_processor


@dataclass
class ChunkStub:
    page_num: int
    text: str
    images: list[Any] = field(default_factory=list)


@dataclass
class SectionStub:
    chunk: ChunkStub


def build_request(payload: dict[str, Any]) -> func.HttpRequest:
    """Construct an HttpRequest carrying the provided payload."""
    body = json.dumps(payload).encode("utf-8")
    return func.HttpRequest(
        method="POST",
        url="http://localhost/api",
        headers={},
        params={},
        body=body,
    )


def build_raw_request(body: bytes) -> func.HttpRequest:
    """Construct an HttpRequest with a raw (non-JSON) payload."""
    return func.HttpRequest(
        method="POST",
        url="http://localhost/api",
        headers={},
        params={},
        body=body,
    )


@pytest.mark.asyncio
async def test_document_extractor_emits_pages_and_figures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Document extractor returns pages with associated figures."""

    class StubParser:
        def __init__(self, pages: Iterable[Any]) -> None:
            self._pages = list(pages)

        async def parse(self, content: Any):
            for page in self._pages:
                yield page

    placeholder = '<figure id="fig-1"></figure>'
    figure = figure_processor.ImageOnPage(
        bytes=TEST_PNG_BYTES,
        bbox=(10.0, 20.0, 30.0, 40.0),
        filename="figure1.png",
        figure_id="fig-1",
        page_num=0,
        placeholder=placeholder,
        title="Drone Logo",
    )
    page_text = f"# Heading\n\n{placeholder}\n\nConclusion."
    page = document_extractor.Page(page_num=0, offset=0, text=page_text, images=[figure])

    # Set up mock file processors and settings
    mock_file_processors = {
        ".pdf": FileProcessor(StubParser([page]), None),
    }

    class MockBlobManager:
        async def download_blob(self, blob_path: str):
            return (b"pdf-bytes", {})

    mock_settings = document_extractor.GlobalSettings(
        file_processors=mock_file_processors,
        azure_credential=object(),
        blob_manager=MockBlobManager(),
        storage_is_adls=False,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=False,
        data_lake_service_client=None,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)

    request_payload = {
        "values": [
            {
                "recordId": "record-1",
                "data": {
                    "metadata_storage_path": "https://account.blob.core.windows.net/container/sample.pdf",
                },
            }
        ]
    }
    response = await document_extractor.extract_document(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    assert result["recordId"] == "record-1"

    data = result["data"]
    assert data["file_name"] == "sample.pdf"
    assert data["pages"] == [
        {"page_num": 0, "text": page_text, "figure_ids": ["fig-1"]},
    ]
    assert len(data["figures"]) == 1
    figure_entry = data["figures"][0]
    assert figure_entry["figure_id"] == "fig-1"
    assert figure_entry["document_file_name"] == "sample.pdf"
    assert figure_entry["bbox"] == [10.0, 20.0, 30.0, 40.0]
    assert figure_entry["bytes_base64"] == base64.b64encode(TEST_PNG_BYTES).decode("utf-8")
    # Verify ACL fields are present (empty when not using ADLS)
    assert data["oids"] == []
    assert data["groups"] == []


@pytest.mark.asyncio
async def test_document_extractor_with_adls_acls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Document extractor extracts ACLs when storage_is_adls=True."""

    class StubParser:
        async def parse(self, content: Any):
            yield document_extractor.Page(page_num=0, offset=0, text="Test content", images=[])

    # Mock file processors and blob manager
    mock_file_processors = {
        ".pdf": FileProcessor(StubParser(), None),
    }

    class MockBlobManager:
        async def download_blob(self, blob_path: str):
            return (b"pdf-bytes", {})

    # Mock DataLakeServiceClient for ACL retrieval
    class MockFileClient:
        async def get_access_control(self, upn: bool = False):
            return {"acl": "user::rwx,user:user-oid-1:r--,group:group-id-1:r-x,other::---"}

    class MockFileSystemClient:
        def get_file_client(self, path):
            return MockFileClient()

    class MockServiceClient:
        def get_file_system_client(self, container):
            return MockFileSystemClient()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    mock_service_client = MockServiceClient()

    mock_settings = document_extractor.GlobalSettings(
        file_processors=mock_file_processors,
        azure_credential=object(),
        blob_manager=MockBlobManager(),
        storage_is_adls=True,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=False,
        data_lake_service_client=mock_service_client,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)

    request_payload = {
        "values": [
            {
                "recordId": "record-1",
                "data": {
                    "metadata_storage_path": "https://account.blob.core.windows.net/container/sample.pdf",
                },
            }
        ]
    }
    response = await document_extractor.extract_document(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]

    data = result["data"]
    # Verify ACL fields are populated from ADLS
    assert data["oids"] == ["user-oid-1"]
    assert data["groups"] == ["group-id-1"]


@pytest.mark.asyncio
async def test_document_extractor_requires_single_record(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = document_extractor.GlobalSettings(
        file_processors={".pdf": FileProcessor(None, None)},
        azure_credential=object(),
        blob_manager=object(),
        storage_is_adls=False,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=False,
        data_lake_service_client=None,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)
    response = await document_extractor.extract_document(build_request({"values": []}))
    assert response.status_code == 500
    body = json.loads(response.get_body().decode("utf-8"))
    assert body["error"]


@pytest.mark.asyncio
async def test_document_extractor_handles_processing_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_process(data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    mock_settings = document_extractor.GlobalSettings(
        file_processors={".pdf": FileProcessor(None, None)},
        azure_credential=object(),
        blob_manager=object(),
        storage_is_adls=False,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=False,
        data_lake_service_client=None,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)
    monkeypatch.setattr(document_extractor, "process_document", failing_process)

    payload = {
        "values": [
            {
                "recordId": "rec-error",
                "data": {
                    "metadata_storage_path": "https://account.blob.core.windows.net/container/sample.pdf",
                },
            }
        ]
    }

    response = await document_extractor.extract_document(build_request(payload))
    assert response.status_code == 200
    values = json.loads(response.get_body().decode("utf-8"))["values"]
    assert values[0]["errors"][0]["message"] == "boom"


@pytest.mark.asyncio
async def test_document_extractor_invalid_json_returns_error() -> None:
    response = await document_extractor.extract_document(build_raw_request(b"not json"))
    assert response.status_code == 500
    body = json.loads(response.get_body().decode("utf-8"))
    assert "error" in body


@pytest.mark.asyncio
async def test_document_extractor_process_document_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingParser:
        async def parse(self, content):
            raise document_extractor.HttpResponseError(message="fail")
            yield  # Make this an async generator

    mock_file_processors = {
        ".pdf": FileProcessor(FailingParser(), None),
    }

    class MockBlobManager:
        async def download_blob(self, blob_path: str):
            return (b"content", {})

    mock_settings = document_extractor.GlobalSettings(
        file_processors=mock_file_processors,
        azure_credential=object(),
        blob_manager=MockBlobManager(),
        storage_is_adls=False,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=False,
        data_lake_service_client=None,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)

    data = {
        "metadata_storage_path": "https://account.blob.core.windows.net/container/doc.pdf",
    }

    with pytest.raises(ValueError) as exc_info:
        await document_extractor.process_document(data)

    assert "Parser failed" in str(exc_info.value)


def test_document_extractor_managed_identity_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set required environment variables
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "teststorage")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "testcontainer")
    monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "testrg")
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-sub-id")

    # Mock setup_blob_manager to avoid actual Azure calls
    monkeypatch.setattr(document_extractor, "setup_blob_manager", lambda **kwargs: object())

    monkeypatch.setenv("AZURE_CLIENT_ID", "client-123")
    document_extractor.configure_global_settings()
    assert isinstance(document_extractor.settings.azure_credential, document_extractor.ManagedIdentityCredential)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    document_extractor.configure_global_settings()


@pytest.mark.asyncio
async def test_figure_processor_returns_enriched_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Figure processor enriches images with URL and description."""

    async def fake_process_page_image(*, image, document_filename: str, **kwargs: Any):
        image.url = f"https://images.example.com/{document_filename}/{image.figure_id}.png"
        image.description = f"Description for {image.figure_id}"
        image.embedding = [0.11, 0.22, 0.33]
        return image

    monkeypatch.setattr(figure_processor, "process_page_image", fake_process_page_image)

    # Create mock settings object
    mock_settings = figure_processor.GlobalSettings(
        blob_manager=object(), figure_processor=object(), image_embeddings=object()
    )
    monkeypatch.setattr(figure_processor, "settings", mock_settings)

    figure = figure_processor.ImageOnPage(
        bytes=TEST_PNG_BYTES,
        bbox=(1.0, 2.0, 3.0, 4.0),
        filename="figure1.png",
        figure_id="fig-1",
        page_num=0,
        placeholder='<figure id="fig-1"></figure>',
    )
    figure_payload = figure.to_skill_payload("sample.pdf")

    request_payload = {
        "values": [
            {
                "recordId": "rec-1",
                "data": figure_payload,
            }
        ]
    }

    response = await figure_processor.process_figure_request(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    assert result["recordId"] == "rec-1"

    data = result["data"]
    assert data["figure_id"] == "fig-1"
    assert data["url"] == "https://images.example.com/sample.pdf/fig-1.png"
    assert data["description"] == "Description for fig-1"
    assert data["embedding"] == [0.11, 0.22, 0.33]
    assert "bytes_base64" not in data


@pytest.mark.asyncio
async def test_figure_processor_invalid_json_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up minimal mock settings so the function can proceed to JSON parsing
    mock_settings = figure_processor.GlobalSettings(blob_manager=object(), figure_processor=None, image_embeddings=None)
    monkeypatch.setattr(figure_processor, "settings", mock_settings)

    response = await figure_processor.process_figure_request(build_raw_request(b"not json"))
    assert response.status_code == 400
    payload = json.loads(response.get_body().decode("utf-8"))
    assert payload["error"] == "Invalid JSON payload"


def test_figure_processor_initialisation_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-456")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "acct")
    monkeypatch.setenv("AZURE_IMAGESTORAGE_CONTAINER", "images")
    monkeypatch.setenv("USE_MULTIMODAL", "true")
    monkeypatch.setenv("AZURE_OPENAI_SERVICE", "svc")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "deploy")
    monkeypatch.setenv("AZURE_VISION_ENDPOINT", "https://vision")

    call_state: dict[str, Any] = {}

    class StubCredential:
        def __init__(self, client_id: str | None = None):
            call_state["credential_client_id"] = client_id

    def fake_setup_blob_manager(**kwargs: Any) -> str:
        call_state["blob_manager_kwargs"] = kwargs
        return "blob"

    def fake_setup_figure_processor(**kwargs: Any) -> str:
        call_state["figure_processor_kwargs"] = kwargs
        return "figproc"

    def fake_setup_openai_client(
        *,
        openai_host: Any,
        azure_credential: Any,
        azure_openai_service: str | None,
        azure_openai_custom_url: str | None,
    ) -> tuple[str, None]:
        call_state["openai_client_args"] = {
            "openai_host": openai_host,
            "azure_credential": azure_credential,
            "azure_openai_service": azure_openai_service,
            "azure_openai_custom_url": azure_openai_custom_url,
        }
        return ("openai-client", None)

    def fake_get_bearer_token_provider(credential: Any, scope: str):
        call_state["token_scope"] = scope
        call_state["token_credential"] = credential
        return lambda: "token"

    class DummyImageEmbeddings:
        def __init__(self, endpoint: str, token_provider):
            self.endpoint = endpoint
            self.token_provider = token_provider

    monkeypatch.setattr(figure_processor, "ManagedIdentityCredential", StubCredential)
    monkeypatch.setattr(figure_processor, "setup_blob_manager", fake_setup_blob_manager)
    monkeypatch.setattr(figure_processor, "setup_figure_processor", fake_setup_figure_processor)
    monkeypatch.setattr(figure_processor, "setup_openai_client", fake_setup_openai_client)
    monkeypatch.setattr(figure_processor, "get_bearer_token_provider", fake_get_bearer_token_provider)
    monkeypatch.setattr(figure_processor, "ImageEmbeddings", DummyImageEmbeddings)
    monkeypatch.setattr(figure_processor, "settings", None)

    figure_processor.configure_global_settings()

    assert figure_processor.settings is not None
    assert figure_processor.settings.blob_manager == "blob"
    assert figure_processor.settings.figure_processor == "figproc"
    embeddings = figure_processor.settings.image_embeddings
    assert isinstance(embeddings, DummyImageEmbeddings)
    assert embeddings.endpoint == "https://vision"
    assert embeddings.token_provider() == "token"

    assert call_state["credential_client_id"] == "client-456"
    assert call_state["blob_manager_kwargs"]["storage_account"] == "acct"
    assert call_state["figure_processor_kwargs"]["use_multimodal"] is True
    assert call_state["token_scope"] == "https://cognitiveservices.azure.com/.default"
    assert isinstance(call_state["token_credential"], StubCredential)
    assert call_state["openai_client_args"]["azure_openai_service"] == "svc"
    assert call_state["openai_client_args"]["azure_credential"] is call_state["token_credential"]


def test_figure_processor_warns_when_openai_incomplete(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """Figure processor is created with warning when USE_MULTIMODAL is true but OpenAI config is incomplete."""
    monkeypatch.setenv("USE_MULTIMODAL", "true")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "acct")
    monkeypatch.setenv("AZURE_IMAGESTORAGE_CONTAINER", "images")
    # OpenAI config missing, so figure_processor will be created but won't work properly
    figure_processor.configure_global_settings()
    # A FigureProcessor object is created even with incomplete config
    assert figure_processor.settings.figure_processor is not None
    assert "USE_MULTIMODAL is true but Azure OpenAI configuration incomplete" in caplog.text


@pytest.mark.asyncio
async def test_text_processor_builds_chunk_with_caption(monkeypatch: pytest.MonkeyPatch) -> None:
    """Text processor merges figure metadata and emits chunk with embeddings."""

    class StubSplitter:
        def split_pages(self, pages: list[Any]):
            for page in pages:
                yield ChunkStub(page_num=page.page_num, text=page.text)

    class StubEmbeddingService:
        async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
            return [[0.41, 0.42, 0.43] for _ in texts]

    # Set up mock file processors with stub splitter
    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), StubSplitter()),
    }

    # Set up mock settings
    mock_settings = text_processor.GlobalSettings(
        use_vectors=True,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=3,
        file_processors=mock_file_processors,
        embedding_service=StubEmbeddingService(),
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    figure = figure_processor.ImageOnPage(
        bytes=TEST_PNG_BYTES,
        bbox=(5.0, 6.0, 7.0, 8.0),
        filename="figure1.png",
        figure_id="fig-1",
        page_num=0,
        placeholder='<figure id="fig-1"></figure>',
        title="Drone Logo",
        url="https://images.example.com/fig-1.png",
        description="A drone-themed company logo.",
    )
    figure_payload = figure.to_skill_payload("financial.pdf")

    page_text = 'Summary paragraph.\n\n<figure id="fig-1"></figure>\n\nClosing remarks.'
    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "financial.pdf",
                        "storageUrl": "https://storage.example.com/content/financial.pdf",
                        "pages": [
                            {"page_num": 0, "text": page_text, "figure_ids": ["fig-1"]},
                        ],
                        "figures": [figure_payload],
                    },
                    "enriched_descriptions": ["A drone-themed company logo."],
                    "enriched_urls": ["https://images.example.com/fig-1.png"],
                    "enriched_embeddings": [[0.51, 0.52, 0.53]],
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    assert result["recordId"] == "doc-1"

    data = result["data"]
    chunks = data["chunks"]
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["parent_id"] == "https://storage.example.com/content/financial.pdf"
    assert chunk["sourcepage"] == "financial.pdf#page=1"
    assert chunk["embedding"] == [0.41, 0.42, 0.43]
    assert chunk["images"] == [
        {
            "url": "https://images.example.com/fig-1.png",
            "description": "A drone-themed company logo.",
            "boundingbox": [5.0, 6.0, 7.0, 8.0],
        }
    ]
    assert '<figure id="fig-1"></figure>' not in chunk["content"]
    assert "A drone-themed company logo." in chunk["content"]
    assert chunk["id"].endswith("-0000")


@pytest.mark.asyncio
async def test_document_extractor_without_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test document extractor returns error when settings not initialized."""
    monkeypatch.setattr(document_extractor, "settings", None)

    request_payload = {
        "values": [
            {
                "recordId": "record-1",
                "data": {
                    "metadata_storage_path": "https://account.blob.core.windows.net/container/sample.pdf",
                },
            }
        ]
    }

    response = await document_extractor.extract_document(build_request(request_payload))

    assert response.status_code == 500
    body = json.loads(response.get_body().decode("utf-8"))
    assert body["error"] == "Settings not initialized"


def test_document_extractor_module_init_key_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Reload module without pytest env to trigger init warning path."""
    import importlib
    from unittest import mock

    saved_env = os.environ.get("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    caplog.set_level("WARNING")

    with mock.patch("azure.identity.aio.ManagedIdentityCredential", lambda *_, **__: object()), mock.patch(
        "prepdocslib.servicesetup.build_file_processors", side_effect=KeyError("missing env")
    ):
        reloaded = importlib.reload(document_extractor)

    assert "Could not initialize settings at module load time" in caplog.text

    monkeypatch.setenv("PYTEST_CURRENT_TEST", "pytest")

    if saved_env is not None:
        monkeypatch.setenv("PYTEST_CURRENT_TEST", saved_env)

    importlib.reload(reloaded)
    reloaded.settings = None


# ACL extraction tests


def setup_acl_mocks(monkeypatch: pytest.MonkeyPatch, acl_string: str, enable_global_document_access: bool = False):
    """Helper to set up mocks for get_file_acls tests."""

    class MockFileClient:
        async def get_access_control(self, upn=False):
            return {"acl": acl_string}

    class MockFileSystemClient:
        def get_file_client(self, path):
            return MockFileClient()

    class MockServiceClient:
        def get_file_system_client(self, container):
            return MockFileSystemClient()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    mock_service_client = MockServiceClient()

    mock_settings = document_extractor.GlobalSettings(
        file_processors={},
        azure_credential=object(),
        blob_manager=object(),
        storage_is_adls=True,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=enable_global_document_access,
        data_lake_service_client=mock_service_client,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)


@pytest.mark.asyncio
async def test_get_file_acls_extracts_user_oids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls extracts user OIDs with read permission."""
    setup_acl_mocks(monkeypatch, "user::rwx,user:user-oid-1:r--,user:user-oid-2:rwx,group::r-x,other::---")

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == ["user-oid-1", "user-oid-2"]
    assert groups == []


@pytest.mark.asyncio
async def test_get_file_acls_extracts_group_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls extracts group IDs with read permission."""
    setup_acl_mocks(monkeypatch, "user::rwx,group::r-x,group:group-id-1:r--,group:group-id-2:r-x,other::---")

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == []
    assert groups == ["group-id-1", "group-id-2"]


@pytest.mark.asyncio
async def test_get_file_acls_ignores_entries_without_read_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls ignores ACL entries without read permission."""
    # user-oid-1 has read, user-oid-2 only has write/execute
    setup_acl_mocks(monkeypatch, "user::rwx,user:user-oid-1:r--,user:user-oid-2:-wx,group:group-id-1:--x,other::---")

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == ["user-oid-1"]
    assert groups == []


@pytest.mark.asyncio
async def test_get_file_acls_other_read_with_global_access_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls returns ['all'] when 'other' has read and global access is enabled."""
    setup_acl_mocks(
        monkeypatch, "user::rwx,user:user-oid-1:r--,group::r-x,other::r--", enable_global_document_access=True
    )

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == ["all"]
    assert groups == ["all"]


@pytest.mark.asyncio
async def test_get_file_acls_other_read_with_global_access_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls does NOT return ['all'] when 'other' has read but global access is disabled."""
    setup_acl_mocks(
        monkeypatch, "user::rwx,user:user-oid-1:r--,group::r-x,other::r--", enable_global_document_access=False
    )

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    # Should return specific user OID, not global access
    assert oids == ["user-oid-1"]
    assert groups == []


@pytest.mark.asyncio
async def test_get_file_acls_other_read_execute_with_global_access_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls returns ['all'] when 'other' has r-x (read+execute) and global access is enabled."""
    setup_acl_mocks(monkeypatch, "user::rwx,group::r-x,other::r-x", enable_global_document_access=True)

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == ["all"]
    assert groups == ["all"]


@pytest.mark.asyncio
async def test_get_file_acls_other_no_read_does_not_grant_global(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls does not grant global access when 'other' has no read permission."""
    # other has only execute, no read - global access enabled but shouldn't trigger
    setup_acl_mocks(
        monkeypatch, "user::rwx,user:user-oid-1:r--,group::r-x,other::--x", enable_global_document_access=True
    )

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    # Should return specific OIDs, not global access
    assert oids == ["user-oid-1"]
    assert groups == []


@pytest.mark.asyncio
async def test_get_file_acls_malformed_acl_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls handles malformed ACL entries gracefully."""
    # Include a malformed entry (missing a colon) mixed with valid entries
    setup_acl_mocks(
        monkeypatch,
        "user::rwx,malformed_entry,user:user-oid-1:r--,invalid:entry,group:group-id-1:r-x",
        enable_global_document_access=False,
    )

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    # Should only include valid entries
    assert oids == ["user-oid-1"]
    assert groups == ["group-id-1"]


@pytest.mark.asyncio
async def test_get_file_acls_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls returns empty lists on exception."""

    class MockServiceClient:
        def get_file_system_client(self, container):
            raise Exception("Connection failed")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    mock_service_client = MockServiceClient()

    mock_settings = document_extractor.GlobalSettings(
        file_processors={},
        azure_credential=object(),
        blob_manager=object(),
        storage_is_adls=True,
        storage_account="account",
        storage_container="container",
        enable_global_document_access=False,
        data_lake_service_client=mock_service_client,
    )
    monkeypatch.setattr(document_extractor, "settings", mock_settings)

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == []
    assert groups == []


@pytest.mark.asyncio
async def test_get_file_acls_raises_without_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls raises RuntimeError when settings not initialized."""
    monkeypatch.setattr(document_extractor, "settings", None)

    with pytest.raises(RuntimeError, match="Global settings not initialized"):
        await document_extractor.get_file_acls("test.pdf")


@pytest.mark.asyncio
async def test_get_file_acls_mixed_users_and_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_file_acls correctly extracts both users and groups."""
    setup_acl_mocks(
        monkeypatch,
        "user::rwx,user:user-1:r--,user:user-2:rwx,group::r-x,group:group-1:r--,group:group-2:r-x,other::---",
    )

    oids, groups = await document_extractor.get_file_acls("test.pdf")

    assert oids == ["user-1", "user-2"]
    assert groups == ["group-1", "group-2"]


@pytest.mark.asyncio
async def test_figure_processor_without_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test figure processor returns error when settings not initialized."""
    monkeypatch.setattr(figure_processor, "settings", None)

    request_payload = {
        "values": [
            {
                "recordId": "img-1",
                "data": {
                    "bytes_base64": base64.b64encode(TEST_PNG_BYTES).decode("utf-8"),
                    "filename": "figure1.png",
                    "figure_id": "fig-1",
                    "document_file_name": "sample.pdf",
                    "page_num": 1,
                },
            }
        ]
    }

    response = await figure_processor.process_figure_request(build_request(request_payload))

    assert response.status_code == 500
    body = json.loads(response.get_body().decode("utf-8"))
    assert body["error"] == "Settings not initialized"


@pytest.mark.asyncio
async def test_text_processor_without_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test text processor returns error when settings not initialized."""
    monkeypatch.setattr(text_processor, "settings", None)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "Some text", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 500
    body = json.loads(response.get_body().decode("utf-8"))
    assert body["error"] == "Settings not initialized"


@pytest.mark.asyncio
async def test_text_processor_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test text processor handles invalid JSON payload."""
    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        embedding_service=None,
        file_processors={},
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Send invalid JSON
    response = await text_processor.process_text_entry(build_raw_request(b"not json"))

    assert response.status_code == 400
    body = json.loads(response.get_body().decode("utf-8"))
    assert body["error"] == "Request body must be valid JSON"


@pytest.mark.asyncio
async def test_text_processor_with_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test text processor uses ManagedIdentityCredential with client ID."""
    # Set the AZURE_CLIENT_ID environment variable
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    text_processor.configure_global_settings()
    # Verify it was configured (actual verification would check the credential type)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    text_processor.configure_global_settings()


@pytest.mark.asyncio
async def test_text_processor_embeddings_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """configure_global_settings wires up embedding service when configuration is complete."""

    monkeypatch.setenv("USE_VECTORS", "true")
    monkeypatch.setenv("AZURE_OPENAI_SERVICE", "svc")
    monkeypatch.setenv("AZURE_OPENAI_EMB_DEPLOYMENT", "deployment")
    monkeypatch.setenv("AZURE_OPENAI_EMB_MODEL_NAME", "model")
    monkeypatch.setenv("OPENAI_HOST", "azure")

    class StubCredential:
        def __init__(self, *args, **kwargs) -> None:
            pass

    monkeypatch.setattr(text_processor, "ManagedIdentityCredential", StubCredential)
    monkeypatch.setattr(text_processor, "build_file_processors", lambda **kwargs: {".pdf": object()})

    calls: dict[str, object] = {}

    def fake_setup_openai_client(**kwargs):
        calls["openai_host"] = kwargs["openai_host"]
        return object(), "https://svc.openai.azure.com"

    def fake_setup_embeddings_service(openai_host, openai_client, **kwargs):
        calls["embedding"] = kwargs
        return "embedding-service"

    monkeypatch.setattr(text_processor, "setup_openai_client", fake_setup_openai_client)
    monkeypatch.setattr(text_processor, "setup_embeddings_service", fake_setup_embeddings_service)

    text_processor.settings = None
    text_processor.configure_global_settings()

    assert calls["openai_host"] == text_processor.OpenAIHost.AZURE
    assert calls["embedding"]["emb_model_name"] == "model"
    assert text_processor.settings is not None
    assert text_processor.settings.embedding_service == "embedding-service"

    text_processor.settings = None


def test_text_processor_configure_logs_when_embedding_config_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("USE_VECTORS", "true")
    monkeypatch.setattr(text_processor, "ManagedIdentityCredential", lambda *args, **kwargs: object())
    monkeypatch.setattr(text_processor, "build_file_processors", lambda **kwargs: {".pdf": object()})

    text_processor.settings = None

    with caplog.at_level(logging.WARNING):
        text_processor.configure_global_settings()

    assert "embedding configuration incomplete" in caplog.text
    assert text_processor.settings is not None
    assert text_processor.settings.embedding_service is None

    text_processor.settings = None


@pytest.mark.asyncio
async def test_text_processor_no_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test text processor handles empty sections."""
    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), SentenceTextSplitter()),
    }
    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        embedding_service=None,
        file_processors=mock_file_processors,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Mock process_text to return empty list
    def mock_process_text(pages, file, splitter, category):
        return []

    monkeypatch.setattr(text_processor, "process_text", mock_process_text)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    assert result["data"]["chunks"] == []


@pytest.mark.asyncio
async def test_text_processor_embeddings_not_initialized(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """Test text processor logs warning when embeddings requested but not initialized."""
    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), SentenceTextSplitter()),
    }
    mock_settings = text_processor.GlobalSettings(
        use_vectors=True,  # Request embeddings
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        embedding_service=None,  # But no service
        file_processors=mock_file_processors,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Mock process_text to return a section
    def mock_process_text(pages, file, splitter, category):
        chunk = ChunkStub(page_num=0, text="Some content", images=[])
        return [SectionStub(chunk=chunk)]

    monkeypatch.setattr(text_processor, "process_text", mock_process_text)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "Some text", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    with caplog.at_level(logging.WARNING):
        await text_processor.process_text_entry(build_request(request_payload))

    assert "Embeddings requested but service not initialised" in caplog.text


@pytest.mark.asyncio
async def test_text_processor_empty_chunk_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test text processor skips empty chunks."""
    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), SentenceTextSplitter()),
    }
    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        embedding_service=None,
        file_processors=mock_file_processors,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Mock process_text to return chunks with empty content
    def mock_process_text(pages, file, splitter, category):
        chunk1 = ChunkStub(page_num=0, text="  ", images=[])  # Whitespace only
        chunk2 = ChunkStub(page_num=0, text="Valid content", images=[])
        return [SectionStub(chunk=chunk1), SectionStub(chunk=chunk2)]

    monkeypatch.setattr(text_processor, "process_text", mock_process_text)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "Some text", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    # Only one chunk should be returned (the empty one is skipped)
    assert len(result["data"]["chunks"]) == 1


@pytest.mark.asyncio
async def test_text_processor_with_multimodal_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test text processor includes image embeddings when use_multimodal is true."""
    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), SentenceTextSplitter()),
    }
    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=True,
        use_acls=False,
        embedding_dimensions=1536,
        embedding_service=None,
        file_processors=mock_file_processors,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Mock process_text to return a section with an image that has embedding
    figure = figure_processor.ImageOnPage(
        bytes=TEST_PNG_BYTES,
        bbox=(5.0, 6.0, 7.0, 8.0),
        filename="figure1.png",
        figure_id="fig-1",
        page_num=0,
        placeholder='<figure id="fig-1"></figure>',
        title="Test Figure",
        description="A test image",
        embedding=[0.1, 0.2, 0.3],
    )

    def mock_process_text(pages, file, splitter, category):
        chunk = ChunkStub(page_num=0, text="Some content", images=[figure])
        return [SectionStub(chunk=chunk)]

    monkeypatch.setattr(text_processor, "process_text", mock_process_text)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "Some text", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    chunks = result["data"]["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["images"][0]["embedding"] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_text_processor_embedding_dimension_mismatch(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """Test text processor logs warning when embedding dimensions don't match."""
    mock_embedding_service = type("MockEmbeddingService", (), {})()

    async def mock_create_embeddings(texts):
        return [[0.1, 0.2]]  # Only 2 dimensions instead of expected 1536

    mock_embedding_service.create_embeddings = mock_create_embeddings

    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), SentenceTextSplitter()),
    }
    mock_settings = text_processor.GlobalSettings(
        use_vectors=True,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,  # Expecting 1536 dimensions
        embedding_service=mock_embedding_service,
        file_processors=mock_file_processors,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Mock process_text to return a section
    def mock_process_text(pages, file, splitter, category):
        chunk = ChunkStub(page_num=0, text="Some content", images=[])
        return [SectionStub(chunk=chunk)]

    monkeypatch.setattr(text_processor, "process_text", mock_process_text)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "Some text", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    with caplog.at_level(logging.WARNING):
        await text_processor.process_text_entry(build_request(request_payload))

    assert "dimension mismatch" in caplog.text


@pytest.mark.asyncio
async def test_text_processor_embeddings_missing_warning(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """Test text processor logs warning when embeddings are requested but missing."""
    mock_embedding_service = type("MockEmbeddingService", (), {})()

    async def mock_create_embeddings(texts):
        # Return None to simulate embeddings service returning None
        return None

    mock_embedding_service.create_embeddings = mock_create_embeddings

    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), SentenceTextSplitter()),
    }
    mock_settings = text_processor.GlobalSettings(
        use_vectors=True,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        embedding_service=mock_embedding_service,
        file_processors=mock_file_processors,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    # Mock process_text to return a section
    def mock_process_text(pages, file, splitter, category):
        chunk = ChunkStub(page_num=0, text="Content 1", images=[])
        return [SectionStub(chunk=chunk)]

    monkeypatch.setattr(text_processor, "process_text", mock_process_text)

    request_payload = {
        "values": [
            {
                "recordId": "doc-1",
                "data": {
                    "consolidated_document": {
                        "file_name": "test.pdf",
                        "storageUrl": "https://storage.example.com/test.pdf",
                        "pages": [{"page_num": 0, "text": "Some text", "figure_ids": []}],
                        "figures": [],
                    },
                },
            }
        ]
    }

    with caplog.at_level(logging.WARNING):
        response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    assert "were requested but missing" in caplog.text


@pytest.mark.asyncio
async def test_text_processor_process_document_handles_missing_figures(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    stub_processor = FileProcessor(TextParser(), SentenceTextSplitter())

    monkeypatch.setattr(text_processor, "select_processor_for_filename", lambda *_args, **_kwargs: stub_processor)
    monkeypatch.setattr(
        text_processor,
        "process_text",
        lambda *args, **kwargs: [SectionStub(chunk=ChunkStub(page_num=0, text="Chunk", images=[]))],
    )

    text_processor.settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        file_processors={".pdf": stub_processor},
        embedding_service=None,
    )

    payload = {
        "consolidated_document": {
            "file_name": "sample.pdf",
            "pages": [
                {
                    "page_num": 0,
                    "text": "Hello",
                    "figure_ids": ["missing", "bad"],
                }
            ],
            "figures": [
                {
                    "figure_id": "bad",
                    # Missing filename forces ImageOnPage.from_skill_payload to raise AssertionError
                }
            ],
        }
    }

    with caplog.at_level(logging.WARNING):
        chunks = await text_processor.process_document(payload)

    assert chunks
    assert any("not found in figures metadata" in record.message for record in caplog.records)
    assert any("Failed to deserialize figure" in record.message for record in caplog.records)

    text_processor.settings = None


@pytest.mark.asyncio
async def test_text_processor_process_document_returns_empty_when_no_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    text_processor.settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=False,
        embedding_dimensions=1536,
        file_processors={},
        embedding_service=None,
    )

    result = await text_processor.process_document({"consolidated_document": {"file_name": "empty.pdf", "pages": []}})

    assert result == []

    text_processor.settings = None


@pytest.mark.asyncio
async def test_text_processor_includes_acls_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Text processor includes oids and groups in chunks when use_acls is enabled."""

    class StubSplitter:
        def split_pages(self, pages: list[Any]):
            for page in pages:
                yield ChunkStub(page_num=page.page_num, text=page.text)

    # Set up mock file processors with stub splitter
    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), StubSplitter()),
    }

    # Set up mock settings with use_acls=True
    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=True,
        embedding_dimensions=3,
        file_processors=mock_file_processors,
        embedding_service=None,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    request_payload = {
        "values": [
            {
                "recordId": "doc-with-acls",
                "data": {
                    "consolidated_document": {
                        "file_name": "secure.pdf",
                        "storageUrl": "https://storage.example.com/content/secure.pdf",
                        "pages": [
                            {"page_num": 0, "text": "Confidential content."},
                        ],
                        "figures": [],
                        # ACL fields are part of consolidated_document (from shaper skill)
                        "oids": ["user-oid-123", "user-oid-456"],
                        "groups": ["group-id-abc"],
                    },
                    "enriched_descriptions": [],
                    "enriched_urls": [],
                    "enriched_embeddings": [],
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]
    assert result["recordId"] == "doc-with-acls"

    data = result["data"]
    chunks = data["chunks"]
    assert len(chunks) == 1
    chunk = chunks[0]
    # Verify ACLs are included in the chunk
    assert chunk["oids"] == ["user-oid-123", "user-oid-456"]
    assert chunk["groups"] == ["group-id-abc"]


@pytest.mark.asyncio
async def test_text_processor_includes_empty_acls_when_enabled_but_none_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Text processor includes empty oids/groups arrays when use_acls is enabled but no ACLs found."""

    class StubSplitter:
        def split_pages(self, pages: list[Any]):
            for page in pages:
                yield ChunkStub(page_num=page.page_num, text=page.text)

    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), StubSplitter()),
    }

    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=True,
        embedding_dimensions=3,
        file_processors=mock_file_processors,
        embedding_service=None,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    request_payload = {
        "values": [
            {
                "recordId": "doc-no-acls",
                "data": {
                    "consolidated_document": {
                        "file_name": "public.pdf",
                        "storageUrl": "https://storage.example.com/content/public.pdf",
                        "pages": [
                            {"page_num": 0, "text": "Public content."},
                        ],
                        "figures": [],
                    },
                    "enriched_descriptions": [],
                    "enriched_urls": [],
                    "enriched_embeddings": [],
                    # No ACL fields provided (or empty)
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]

    data = result["data"]
    chunks = data["chunks"]
    assert len(chunks) == 1
    chunk = chunks[0]
    # Verify empty ACL arrays are included to distinguish "no ACLs" from "ACLs not extracted"
    assert chunk["oids"] == []
    assert chunk["groups"] == []


@pytest.mark.asyncio
async def test_text_processor_excludes_acls_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Text processor does not include oids/groups in chunks when use_acls is disabled."""

    class StubSplitter:
        def split_pages(self, pages: list[Any]):
            for page in pages:
                yield ChunkStub(page_num=page.page_num, text=page.text)

    mock_file_processors = {
        ".pdf": FileProcessor(TextParser(), StubSplitter()),
    }

    mock_settings = text_processor.GlobalSettings(
        use_vectors=False,
        use_multimodal=False,
        use_acls=False,  # ACLs disabled
        embedding_dimensions=3,
        file_processors=mock_file_processors,
        embedding_service=None,
    )
    monkeypatch.setattr(text_processor, "settings", mock_settings)

    request_payload = {
        "values": [
            {
                "recordId": "doc-acls-disabled",
                "data": {
                    "consolidated_document": {
                        "file_name": "noauth.pdf",
                        "storageUrl": "https://storage.example.com/content/noauth.pdf",
                        "pages": [
                            {"page_num": 0, "text": "Content without auth."},
                        ],
                        "figures": [],
                    },
                    "enriched_descriptions": [],
                    "enriched_urls": [],
                    "enriched_embeddings": [],
                    # ACL fields present in input but should be ignored
                    "oids": ["user-oid-123"],
                    "groups": ["group-id-abc"],
                },
            }
        ]
    }

    response = await text_processor.process_text_entry(build_request(request_payload))

    assert response.status_code == 200
    body = json.loads(response.get_body().decode("utf-8"))
    values = body["values"]
    assert len(values) == 1
    result = values[0]

    data = result["data"]
    chunks = data["chunks"]
    assert len(chunks) == 1
    chunk = chunks[0]
    # Verify ACL fields are NOT included when use_acls is disabled
    assert "oids" not in chunk
    assert "groups" not in chunk


def test_text_processor_module_init_logs_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import importlib
    from unittest import mock

    saved_env = os.environ.get("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    class StubCredential:
        def __init__(self, *args, **kwargs) -> None:
            pass

    caplog.set_level("WARNING")

    with mock.patch("azure.identity.aio.ManagedIdentityCredential", StubCredential), mock.patch(
        "prepdocslib.servicesetup.build_file_processors", side_effect=KeyError("missing env")
    ), mock.patch("prepdocslib.servicesetup.setup_openai_client", return_value=(object(), None)), mock.patch(
        "prepdocslib.servicesetup.setup_embeddings_service", return_value=None
    ):
        reloaded = importlib.reload(text_processor)

    assert "Could not initialize settings at module load time" in caplog.text

    monkeypatch.setenv("PYTEST_CURRENT_TEST", "pytest")

    if saved_env is not None:
        monkeypatch.setenv("PYTEST_CURRENT_TEST", saved_env)

    importlib.reload(reloaded)
    reloaded.settings = None
