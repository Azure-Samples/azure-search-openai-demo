import pytest

from prepdocslib.servicesetup import (
    OpenAIHost,
    setup_blob_manager,
    setup_embeddings_service,
    setup_openai_client,
)

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

    import prepdocslib.servicesetup as servicesetup_module

    monkeypatch.setattr(servicesetup_module, "BlobManager", StubBlobManager)

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
    import openai
    from openai.types.create_embedding_response import Usage

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

    from prepdocslib.embeddings import OpenAIEmbeddings

    assert isinstance(embeddings, OpenAIEmbeddings)
    assert embeddings.azure_deployment_name == "deployment"
    assert embeddings.azure_endpoint == "https://service.openai.azure.com"


def test_setup_embeddings_service_requires_endpoint_for_azure() -> None:
    import openai
    from openai.types.create_embedding_response import Usage

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
    import openai
    from openai.types.create_embedding_response import Usage

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

    import prepdocslib.servicesetup as servicesetup_module

    monkeypatch.setattr(servicesetup_module, "AsyncOpenAI", StubAsyncOpenAI)
    monkeypatch.setattr(servicesetup_module, "get_bearer_token_provider", lambda *args, **kwargs: lambda: "fake_token")

    client, endpoint = setup_openai_client(
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

    import prepdocslib.servicesetup as servicesetup_module

    monkeypatch.setattr(servicesetup_module, "AsyncOpenAI", StubAsyncOpenAI)

    client, endpoint = setup_openai_client(
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

    import prepdocslib.servicesetup as servicesetup_module

    monkeypatch.setattr(servicesetup_module, "AsyncOpenAI", StubAsyncOpenAI)

    client, endpoint = setup_openai_client(
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
    from prepdocslib.servicesetup import setup_search_info

    with pytest.raises(ValueError, match="SearchAgent model must be specified"):
        setup_search_info(
            azure_credential=MockAzureCredential(),
            search_service="mysearch",
            index_name="myindex",
            use_agentic_retrieval=True,
            azure_openai_searchagent_model=None,
        )


def test_setup_image_embeddings_multimodal_without_vision():
    """Test that setup_image_embeddings_service raises ValueError when using multimodal without vision endpoint."""
    from prepdocslib.servicesetup import setup_image_embeddings_service

    with pytest.raises(ValueError, match="Azure AI Vision endpoint must be provided"):
        setup_image_embeddings_service(
            use_multimodal=True,
            vision_endpoint=None,
            azure_credential=MockAzureCredential(),
        )


def test_setup_figure_processor_content_understanding():
    """Test that setup_figure_processor returns correct processor for content understanding."""
    from prepdocslib.figureprocessor import FigureProcessor, MediaDescriptionStrategy
    from prepdocslib.servicesetup import setup_figure_processor

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


def test_setup_parser_document_intelligence_with_key():
    """Test that select_parser uses key credential when provided."""
    from prepdocslib.pdfparser import DocumentAnalysisParser
    from prepdocslib.servicesetup import select_parser

    parser = select_parser(
        file_name="test.pdf",
        content_type="application/pdf",
        azure_credential=MockAzureCredential(),
        document_intelligence_service="myservice",
        document_intelligence_key="my-key",
        use_local_html_parser=False,
    )

    assert isinstance(parser, DocumentAnalysisParser)


def test_setup_parser_text_file():
    """Test that select_parser returns TextParser for text files."""
    from prepdocslib.servicesetup import select_parser
    from prepdocslib.textparser import TextParser

    parser = select_parser(
        file_name="test.txt",
        content_type="text/plain",
        azure_credential=MockAzureCredential(),
        document_intelligence_service=None,
    )

    assert isinstance(parser, TextParser)


def test_setup_parser_application_type_with_di():
    """Test that select_parser uses DI for application/* content types."""
    from prepdocslib.pdfparser import DocumentAnalysisParser
    from prepdocslib.servicesetup import select_parser

    parser = select_parser(
        file_name="test.unknown",
        content_type="application/unknown",
        azure_credential=MockAzureCredential(),
        document_intelligence_service="myservice",
    )

    assert isinstance(parser, DocumentAnalysisParser)


def test_setup_parser_unsupported_file_type():
    """Test that select_parser raises ValueError for unsupported file types."""
    from prepdocslib.servicesetup import select_parser

    with pytest.raises(ValueError, match="Unsupported file type"):
        select_parser(
            file_name="test.xyz",
            content_type="application/xyz",
            azure_credential=MockAzureCredential(),
            document_intelligence_service=None,
        )
