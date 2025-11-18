import openai
import pytest
from openai.types.create_embedding_response import Usage

from prepdocslib.embeddings import OpenAIEmbeddings
from prepdocslib.figureprocessor import FigureProcessor, MediaDescriptionStrategy
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.pdfparser import DocumentAnalysisParser
from prepdocslib.servicesetup import (
    OpenAIHost,
    build_file_processors,
    clean_key_if_exists,
    select_processor_for_filename,
    setup_blob_manager,
    setup_embeddings_service,
    setup_figure_processor,
    setup_image_embeddings_service,
    setup_openai_client,
    setup_search_info,
)
from prepdocslib.textparser import TextParser

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
    MockAzureCredential,
)
from .test_prepdocs import MockClient, MockEmbeddingsClient


def test_setup_blob_manager_respects_storage_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubBlobManager:
        def __init__(
            self,
            *,
            endpoint: str,
            container: str,
            account: str,
            credential: object,
            resource_group: str,
            subscription_id: str,
            image_container: str | None = None,
        ) -> None:
            captured["endpoint"] = endpoint
            captured["container"] = container
            captured["account"] = account
            captured["credential"] = credential
            captured["resource_group"] = resource_group
            captured["subscription_id"] = subscription_id
            captured["image_container"] = image_container

    monkeypatch.setattr("prepdocslib.servicesetup.BlobManager", StubBlobManager)

    result = setup_blob_manager(
        azure_credential=MockAzureCredential(),
        storage_account="storageacct",
        storage_container="docs",
        storage_resource_group="rg",
        subscription_id="sub-id",
        storage_key="override-key",
        image_storage_container="images",
    )

    assert isinstance(result, StubBlobManager)
    assert captured["credential"] == "override-key"
    assert captured["image_container"] == "images"


def test_setup_embeddings_service_populates_azure_metadata() -> None:
    embeddings = setup_embeddings_service(
        open_ai_client=MockClient(
            MockEmbeddingsClient(
                openai.types.CreateEmbeddingResponse(
                    object="list",
                    data=[],
                    model="text-embedding-3-large",
                    usage=Usage(prompt_tokens=0, total_tokens=0),
                )
            )
        ),
        openai_host=OpenAIHost.AZURE,
        emb_model_name=MOCK_EMBEDDING_MODEL_NAME,
        emb_model_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        azure_openai_deployment="deployment",
        azure_openai_endpoint="https://service.openai.azure.com",
    )

    assert isinstance(embeddings, OpenAIEmbeddings)
    assert embeddings.azure_deployment_name == "deployment"
    assert embeddings.azure_endpoint == "https://service.openai.azure.com"


def test_setup_embeddings_service_requires_endpoint_for_azure() -> None:
    with pytest.raises(ValueError):
        setup_embeddings_service(
            open_ai_client=MockClient(
                MockEmbeddingsClient(
                    openai.types.CreateEmbeddingResponse(
                        object="list",
                        data=[],
                        model="text-embedding-3-large",
                        usage=Usage(prompt_tokens=0, total_tokens=0),
                    )
                )
            ),
            openai_host=OpenAIHost.AZURE,
            emb_model_name=MOCK_EMBEDDING_MODEL_NAME,
            emb_model_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            azure_openai_deployment="deployment",
            azure_openai_endpoint=None,
        )


def test_setup_embeddings_service_requires_deployment_for_azure() -> None:
    with pytest.raises(ValueError):
        setup_embeddings_service(
            open_ai_client=MockClient(
                MockEmbeddingsClient(
                    openai.types.CreateEmbeddingResponse(
                        object="list",
                        data=[],
                        model="text-embedding-3-large",
                        usage=Usage(prompt_tokens=0, total_tokens=0),
                    )
                )
            ),
            openai_host=OpenAIHost.AZURE,
            emb_model_name=MOCK_EMBEDDING_MODEL_NAME,
            emb_model_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            azure_openai_deployment=None,
            azure_openai_endpoint="https://service.openai.azure.com",
        )


def test_setup_openai_client_azure_constructs_endpoint_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that setup_openai_client correctly constructs the Azure OpenAI endpoint URL from service name."""
    captured_base_url: list[str] = []

    class StubAsyncOpenAI:
        def __init__(self, *, base_url: str, api_key, **kwargs) -> None:
            captured_base_url.append(base_url)

    monkeypatch.setattr("prepdocslib.servicesetup.AsyncOpenAI", StubAsyncOpenAI)
    monkeypatch.setattr(
        "prepdocslib.servicesetup.get_bearer_token_provider", lambda *args, **kwargs: lambda: "fake_token"
    )

    _, endpoint = setup_openai_client(
        openai_host=OpenAIHost.AZURE,
        azure_credential=MockAzureCredential(),
        azure_openai_service="myopenaiservice",
    )

    # Verify the endpoint is constructed correctly
    assert endpoint == "https://myopenaiservice.openai.azure.com"
    # Verify the base_url includes the endpoint with the openai/v1 suffix
    assert captured_base_url[0] == "https://myopenaiservice.openai.azure.com/openai/v1"


def test_setup_openai_client_azure_custom_uses_custom_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that setup_openai_client uses the custom URL for azure_custom host."""
    captured_base_url: list[str] = []

    class StubAsyncOpenAI:
        def __init__(self, *, base_url: str, api_key, **kwargs) -> None:
            captured_base_url.append(base_url)

    monkeypatch.setattr("prepdocslib.servicesetup.AsyncOpenAI", StubAsyncOpenAI)

    _, endpoint = setup_openai_client(
        openai_host=OpenAIHost.AZURE_CUSTOM,
        azure_credential=MockAzureCredential(),
        azure_openai_custom_url="https://custom.endpoint.com/openai",
        azure_openai_api_key="test-key",
    )

    # Verify the custom URL is used
    assert captured_base_url[0] == "https://custom.endpoint.com/openai"
    # Verify endpoint is None for custom URLs
    assert endpoint is None


def test_setup_openai_client_azure_respects_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that setup_openai_client uses the API key override when provided."""
    captured_api_key: list[str] = []

    class StubAsyncOpenAI:
        def __init__(self, *, base_url: str, api_key: str, **kwargs) -> None:
            captured_api_key.append(api_key)

    monkeypatch.setattr("prepdocslib.servicesetup.AsyncOpenAI", StubAsyncOpenAI)

    setup_openai_client(
        openai_host=OpenAIHost.AZURE,
        azure_credential=MockAzureCredential(),
        azure_openai_service="myopenaiservice",
        azure_openai_api_key="my-api-key-override",
    )

    assert captured_api_key[0] == "my-api-key-override"


def test_setup_openai_client_openai_requires_api_key() -> None:
    """Test that setup_openai_client raises ValueError when using OpenAI without API key."""
    with pytest.raises(ValueError, match="OpenAI key is required"):
        setup_openai_client(
            openai_host=OpenAIHost.OPENAI,
            azure_credential=MockAzureCredential(),
            openai_api_key=None,
        )


def test_setup_openai_client_azure_requires_service() -> None:
    """Test that setup_openai_client raises ValueError when using Azure without service name."""
    with pytest.raises(ValueError, match="AZURE_OPENAI_SERVICE must be set"):
        setup_openai_client(
            openai_host=OpenAIHost.AZURE,
            azure_credential=MockAzureCredential(),
            azure_openai_service=None,
        )


def test_setup_openai_client_azure_custom_requires_url() -> None:
    """Test that setup_openai_client raises ValueError when using azure_custom without custom URL."""
    with pytest.raises(ValueError, match="AZURE_OPENAI_CUSTOM_URL must be set"):
        setup_openai_client(
            openai_host=OpenAIHost.AZURE_CUSTOM,
            azure_credential=MockAzureCredential(),
            azure_openai_custom_url=None,
        )


def test_setup_search_info_agentic_retrieval_without_model():
    """Test that setup_search_info raises ValueError when using agentic retrieval without search agent model."""
    with pytest.raises(ValueError, match="Azure OpenAI deployment for Knowledge Base must be specified"):
        setup_search_info(
            azure_credential=MockAzureCredential(),
            search_service="mysearch",
            index_name="myindex",
            use_agentic_knowledgebase=True,
            azure_openai_knowledgebase_deployment=None,
        )


def test_setup_image_embeddings_multimodal_without_vision():
    """Test that setup_image_embeddings_service raises ValueError when using multimodal without vision endpoint."""
    with pytest.raises(ValueError, match="Azure AI Vision endpoint must be provided"):
        setup_image_embeddings_service(
            use_multimodal=True,
            vision_endpoint=None,
            azure_credential=MockAzureCredential(),
        )


def test_setup_figure_processor_content_understanding():
    """Test that setup_figure_processor returns correct processor for content understanding."""
    processor = setup_figure_processor(
        use_multimodal=False,
        use_content_understanding=True,
        content_understanding_endpoint="https://example.com",
        credential=MockAzureCredential(),
        openai_client=None,
        openai_model=None,
        openai_deployment=None,
    )

    assert isinstance(processor, FigureProcessor)
    assert processor.strategy == MediaDescriptionStrategy.CONTENTUNDERSTANDING


def test_build_file_processors_with_document_intelligence_key():
    """Test that build_file_processors uses key credential when provided."""
    file_processors = build_file_processors(
        azure_credential=MockAzureCredential(),
        document_intelligence_service="myservice",
        document_intelligence_key="my-key",
        use_local_pdf_parser=False,
        use_local_html_parser=False,
    )

    assert ".pdf" in file_processors
    assert isinstance(file_processors[".pdf"].parser, DocumentAnalysisParser)


def test_build_file_processors_text_files():
    """Test that build_file_processors includes text file parsers."""
    file_processors = build_file_processors(
        azure_credential=MockAzureCredential(),
        document_intelligence_service=None,
    )

    assert ".txt" in file_processors
    assert isinstance(file_processors[".txt"].parser, TextParser)
    assert ".md" in file_processors
    assert isinstance(file_processors[".md"].parser, TextParser)


def test_build_file_processors_with_di_enables_office_formats():
    """Test that build_file_processors includes Office formats when DI is available."""
    file_processors = build_file_processors(
        azure_credential=MockAzureCredential(),
        document_intelligence_service="myservice",
    )

    assert ".docx" in file_processors
    assert ".pptx" in file_processors
    assert ".xlsx" in file_processors
    assert isinstance(file_processors[".docx"].parser, DocumentAnalysisParser)


def test_build_file_processors_without_di_excludes_office_formats():
    """Test that build_file_processors excludes Office formats when DI is not available."""
    file_processors = build_file_processors(
        azure_credential=MockAzureCredential(),
        document_intelligence_service=None,
    )

    assert ".docx" not in file_processors
    assert ".pptx" not in file_processors
    assert ".xlsx" not in file_processors


def test_clean_key_if_exists_handles_whitespace() -> None:
    assert clean_key_if_exists("  secret  ") == "secret"
    assert clean_key_if_exists("   ") is None
    assert clean_key_if_exists(None) is None


def test_build_file_processors_logs_when_no_parsers(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("WARNING")
    monkeypatch.setattr("prepdocslib.servicesetup.DocumentAnalysisParser", lambda *args, **kwargs: None)

    processors = build_file_processors(
        azure_credential=MockAzureCredential(),
        document_intelligence_service="service",
        use_local_pdf_parser=False,
        use_local_html_parser=False,
    )

    assert ".pdf" not in processors
    assert ".html" not in processors
    warnings = {record.message for record in caplog.records}
    assert any("No PDF parser available" in message for message in warnings)
    assert any("No HTML parser available" in message for message in warnings)


def test_select_processor_for_filename_raises_when_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported file type: file.unsupported"):
        select_processor_for_filename("file.unsupported", {".txt": FileProcessor(TextParser(), None)})
