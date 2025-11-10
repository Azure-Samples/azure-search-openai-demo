import base64
import importlib
import json
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import azure.functions as func
import pytest

from document_extractor import function_app as document_extractor
from figure_processor import function_app as figure_processor
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


@contextmanager
def restore_module_state(module, attributes: list[str]):
    saved = {name: getattr(module, name) for name in attributes}
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(module, name, value)


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

    monkeypatch.setattr(document_extractor, "select_parser", lambda **_: StubParser([page]))

    request_payload = {
        "values": [
            {
                "recordId": "record-1",
                "data": {
                    "file_data": {"$type": "file", "data": base64.b64encode(b"pdf-bytes").decode("utf-8")},
                    "file_name": "sample.pdf",
                    "contentType": "application/pdf",
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


@pytest.mark.asyncio
async def test_document_extractor_requires_single_record() -> None:
    response = await document_extractor.extract_document(build_request({"values": []}))
    assert response.status_code == 500
    body = json.loads(response.get_body().decode("utf-8"))
    assert body["error"]


@pytest.mark.asyncio
async def test_document_extractor_handles_processing_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_process(data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(document_extractor, "process_document", failing_process)

    payload = {
        "values": [
            {
                "recordId": "rec-error",
                "data": {
                    "file_data": {"$type": "file", "data": base64.b64encode(b"pdf-bytes").decode("utf-8")},
                    "file_name": "sample.pdf",
                    "contentType": "application/pdf",
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

    monkeypatch.setattr(document_extractor, "select_parser", lambda **_: FailingParser())

    data = {
        "file_data": {"data": base64.b64encode(b"content").decode("utf-8")},
        "file_name": "doc.pdf",
        "contentType": "application/pdf",
    }

    with pytest.raises(ValueError) as exc_info:
        await document_extractor.process_document(data)

    assert "Parser failed" in str(exc_info.value)


def test_document_extractor_missing_file_data() -> None:
    with pytest.raises(ValueError):
        document_extractor.get_document_stream_filedata({"file_data": {}})


def test_document_extractor_managed_identity_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-123")
    module = importlib.reload(document_extractor)
    assert isinstance(module.AZURE_CREDENTIAL, module.ManagedIdentityCredential)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    importlib.reload(document_extractor)


@pytest.mark.asyncio
async def test_figure_processor_returns_enriched_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Figure processor enriches images with URL and description."""

    async def fake_process_page_image(*, image, document_filename: str, **kwargs: Any):
        image.url = f"https://images.example.com/{document_filename}/{image.figure_id}.png"
        image.description = f"Description for {image.figure_id}"
        image.embedding = [0.11, 0.22, 0.33]
        return image

    monkeypatch.setattr(figure_processor, "process_page_image", fake_process_page_image)
    monkeypatch.setattr(figure_processor, "BLOB_MANAGER", object())
    monkeypatch.setattr(figure_processor, "FIGURE_PROCESSOR", object())
    monkeypatch.setattr(figure_processor, "IMAGE_EMBEDDINGS", object())

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
async def test_figure_processor_invalid_json_returns_error() -> None:
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

    import sys
    from pathlib import Path

    fp_root = Path(__file__).parent.parent / "app" / "functions" / "figure_processor"
    sys.path.insert(0, str(fp_root))

    fp_servicesetup = importlib.import_module("prepdocslib.servicesetup")
    fp_embeddings = importlib.import_module("prepdocslib.embeddings")

    monkeypatch.setattr(fp_servicesetup, "setup_blob_manager", lambda **_: "blob")
    monkeypatch.setattr(fp_servicesetup, "setup_figure_processor", lambda **_: "figproc")
    monkeypatch.setattr(fp_servicesetup, "setup_openai_client", lambda **_: "openai-client")

    class DummyImageEmbeddings:
        def __init__(self, endpoint: str, token_provider):
            self.endpoint = endpoint
            self.token_provider = token_provider

    monkeypatch.setattr(fp_embeddings, "ImageEmbeddings", DummyImageEmbeddings)
    monkeypatch.setattr("azure.identity.aio.get_bearer_token_provider", lambda *_, **__: lambda: "token")

    module = importlib.reload(figure_processor)
    assert module.BLOB_MANAGER == "blob"
    assert module.FIGURE_PROCESSOR == "figproc"
    assert isinstance(module.IMAGE_EMBEDDINGS, DummyImageEmbeddings)

    # Reset module to default configuration for subsequent tests
    for var in [
        "AZURE_CLIENT_ID",
        "AZURE_STORAGE_ACCOUNT",
        "AZURE_IMAGESTORAGE_CONTAINER",
        "USE_MULTIMODAL",
        "AZURE_OPENAI_SERVICE",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
        "AZURE_VISION_ENDPOINT",
    ]:
        monkeypatch.delenv(var, raising=False)
    sys.path.remove(str(fp_root))
    importlib.reload(figure_processor)


def test_figure_processor_warns_when_openai_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Figure processor is None when USE_MULTIMODAL is true but OpenAI config is incomplete."""
    monkeypatch.setenv("USE_MULTIMODAL", "true")
    # OpenAI config missing, so FIGURE_PROCESSOR should be None
    module = importlib.reload(figure_processor)
    # Without OpenAI or Content Understanding config, processor is None
    assert module.FIGURE_PROCESSOR is None
    monkeypatch.delenv("USE_MULTIMODAL", raising=False)
    importlib.reload(figure_processor)


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

    monkeypatch.setattr(text_processor, "SENTENCE_SPLITTER", StubSplitter())
    monkeypatch.setattr(text_processor, "EMBEDDING_SERVICE", StubEmbeddingService())
    monkeypatch.setattr(text_processor, "AZURE_OPENAI_EMB_DIMENSIONS", 3)
    monkeypatch.setattr(text_processor, "USE_MULTIMODAL", False)

    figure = figure_processor.ImageOnPage(
        bytes=TEST_PNG_BYTES,
        bbox=(5.0, 6.0, 7.0, 8.0),
        filename="figure1.png",
        figure_id="fig-1",
        page_num=0,
        placeholder='<figure id="fig-1"></figure>',
        title="Drone Logo",
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
