"""Shared service setup helpers."""

import logging
import os
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from openai import AsyncOpenAI

from .blobmanager import BlobManager
from .csvparser import CsvParser
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .figureprocessor import FigureProcessor, MediaDescriptionStrategy
from .fileprocessor import FileProcessor
from .htmlparser import LocalHTMLParser
from .jsonparser import JsonParser
from .parser import Parser
from .pdfparser import DocumentAnalysisParser, LocalPdfParser
from .strategy import SearchInfo
from .textparser import TextParser
from .textsplitter import SentenceTextSplitter, SimpleTextSplitter

logger = logging.getLogger("scripts")


def clean_key_if_exists(key: Optional[str]) -> Optional[str]:
    """Remove leading and trailing whitespace from a key if it exists. If the key is empty, return None."""
    if key is not None and key.strip() != "":
        return key.strip()
    return None


class OpenAIHost(str, Enum):
    """Supported OpenAI hosting styles.

    OPENAI:       Public OpenAI API.
    AZURE:        Standard Azure OpenAI (service name becomes endpoint).
    AZURE_CUSTOM: A fully custom endpoint URL (for Network Isolation / APIM).
    LOCAL:        A locally hosted OpenAI-compatible endpoint (no key required).
    """

    OPENAI = "openai"
    AZURE = "azure"
    AZURE_CUSTOM = "azure_custom"
    LOCAL = "local"


def setup_search_info(
    search_service: str,
    index_name: str,
    azure_credential: AsyncTokenCredential,
    use_agentic_knowledgebase: Optional[bool] = None,
    azure_openai_endpoint: Optional[str] = None,
    knowledgebase_name: Optional[str] = None,
    azure_openai_knowledgebase_deployment: Optional[str] = None,
    azure_openai_knowledgebase_model: Optional[str] = None,
    search_key: Optional[str] = None,
    azure_vision_endpoint: Optional[str] = None,
) -> SearchInfo:
    """Setup search service information."""
    search_creds: AsyncTokenCredential | AzureKeyCredential = (
        azure_credential if search_key is None else AzureKeyCredential(search_key)
    )
    if use_agentic_knowledgebase and azure_openai_knowledgebase_deployment is None:
        raise ValueError("Azure OpenAI deployment for Knowledge Base must be specified for agentic retrieval.")

    return SearchInfo(
        endpoint=f"https://{search_service}.search.windows.net/",
        credential=search_creds,
        index_name=index_name,
        knowledgebase_name=knowledgebase_name,
        use_agentic_knowledgebase=use_agentic_knowledgebase,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_knowledgebase_model=azure_openai_knowledgebase_model,
        azure_openai_knowledgebase_deployment=azure_openai_knowledgebase_deployment,
        azure_vision_endpoint=azure_vision_endpoint,
    )


def setup_openai_client(
    openai_host: OpenAIHost,
    azure_credential: AsyncTokenCredential,
    azure_openai_api_key: Optional[str] = None,
    azure_openai_service: Optional[str] = None,
    azure_openai_custom_url: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openai_organization: Optional[str] = None,
) -> tuple[AsyncOpenAI, Optional[str]]:
    openai_client: AsyncOpenAI
    azure_openai_endpoint: Optional[str] = None

    if openai_host in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        base_url: Optional[str] = None
        api_key_or_token: Optional[str | Callable[[], Awaitable[str]]] = None
        if openai_host == OpenAIHost.AZURE_CUSTOM:
            logger.info("OPENAI_HOST is azure_custom, setting up Azure OpenAI custom client")
            if not azure_openai_custom_url:
                raise ValueError("AZURE_OPENAI_CUSTOM_URL must be set when OPENAI_HOST is azure_custom")
            base_url = azure_openai_custom_url
        else:
            logger.info("OPENAI_HOST is azure, setting up Azure OpenAI client")
            if not azure_openai_service:
                raise ValueError("AZURE_OPENAI_SERVICE must be set when OPENAI_HOST is azure")
            azure_openai_endpoint = f"https://{azure_openai_service}.openai.azure.com"
            base_url = f"{azure_openai_endpoint}/openai/v1"
        if azure_openai_api_key:
            logger.info("AZURE_OPENAI_API_KEY_OVERRIDE found, using as api_key for Azure OpenAI client")
            api_key_or_token = azure_openai_api_key
        else:
            logger.info("Using Azure credential (passwordless authentication) for Azure OpenAI client")
            api_key_or_token = get_bearer_token_provider(
                azure_credential, "https://cognitiveservices.azure.com/.default"
            )
        openai_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key_or_token,
        )
    elif openai_host == OpenAIHost.LOCAL:
        logger.info("OPENAI_HOST is local, setting up local OpenAI client for OPENAI_BASE_URL with no key")
        openai_client = AsyncOpenAI(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key="no-key-required",
        )
    else:
        logger.info(
            "OPENAI_HOST is not azure, setting up OpenAI client using OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables"
        )
        if openai_api_key is None:
            raise ValueError("OpenAI key is required when using the non-Azure OpenAI API")
        openai_client = AsyncOpenAI(
            api_key=openai_api_key,
            organization=openai_organization,
        )
    return openai_client, azure_openai_endpoint


def setup_image_embeddings_service(
    azure_credential: AsyncTokenCredential,
    vision_endpoint: Optional[str],
    use_multimodal: bool,
) -> ImageEmbeddings | None:
    image_embeddings_service: Optional[ImageEmbeddings] = None
    if use_multimodal:
        if vision_endpoint is None:
            raise ValueError("An Azure AI Vision endpoint must be provided to use multimodal features.")
        image_embeddings_service = ImageEmbeddings(
            endpoint=vision_endpoint,
            token_provider=get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default"),
        )
    return image_embeddings_service


def setup_embeddings_service(
    openai_host: OpenAIHost,
    open_ai_client: AsyncOpenAI,
    emb_model_name: str,
    emb_model_dimensions: int,
    azure_openai_deployment: Optional[str] = None,
    azure_openai_endpoint: Optional[str] = None,
    disable_batch: bool = False,
) -> OpenAIEmbeddings:
    if openai_host in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        if azure_openai_endpoint is None:
            raise ValueError("Azure OpenAI endpoint must be provided when using Azure OpenAI embeddings")
        if azure_openai_deployment is None:
            raise ValueError("Azure OpenAI deployment must be provided when using Azure OpenAI embeddings")

    return OpenAIEmbeddings(
        open_ai_client=open_ai_client,
        open_ai_model_name=emb_model_name,
        open_ai_dimensions=emb_model_dimensions,
        disable_batch=disable_batch,
        azure_deployment_name=azure_openai_deployment,
        azure_endpoint=azure_openai_endpoint,
    )


def setup_blob_manager(
    azure_credential: AsyncTokenCredential | str,
    storage_account: str,
    storage_container: str,
    storage_resource_group: Optional[str] = None,
    subscription_id: Optional[str] = None,
    storage_key: Optional[str] = None,
    image_storage_container: Optional[str] = None,
) -> BlobManager:
    """Create a BlobManager instance for document or figure storage.

    The optional resource group and subscription are retained for parity with
    local ingestion (used for diagnostic operations) but not required by
    Azure Functions.
    The optional image storage container is used for the multimodal ingestion feature.
    """
    endpoint = f"https://{storage_account}.blob.core.windows.net"
    storage_credential: AsyncTokenCredential | str = azure_credential if storage_key is None else storage_key

    return BlobManager(
        endpoint=endpoint,
        container=storage_container,
        account=storage_account,
        credential=storage_credential,
        resource_group=storage_resource_group,
        subscription_id=subscription_id,
        image_container=image_storage_container,
    )


def setup_figure_processor(
    *,
    credential: AsyncTokenCredential | None,
    use_multimodal: bool,
    use_content_understanding: bool,
    content_understanding_endpoint: str | None,
    openai_client: object | None,
    openai_model: str | None,
    openai_deployment: str | None,
) -> FigureProcessor | None:
    """Create a FigureProcessor based on feature flags.

    Priority order:
      1. use_multimodal -> MediaDescriptionStrategy.OPENAI
      2. else if use_content_understanding and endpoint -> CONTENTUNDERSTANDING
      3. else -> return None (no figure description)
    """
    if use_multimodal:
        return FigureProcessor(
            credential=credential,
            strategy=MediaDescriptionStrategy.OPENAI,
            openai_client=openai_client,
            openai_model=openai_model,
            openai_deployment=openai_deployment,
        )
    if use_content_understanding and content_understanding_endpoint:
        return FigureProcessor(
            credential=credential,
            strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
            content_understanding_endpoint=content_understanding_endpoint,
        )
    return None


def build_file_processors(
    *,
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: str | None,
    document_intelligence_key: str | None = None,
    use_local_pdf_parser: bool = False,
    use_local_html_parser: bool = False,
    process_figures: bool = False,
) -> dict[str, FileProcessor]:
    sentence_text_splitter = SentenceTextSplitter()

    doc_int_parser: Optional[DocumentAnalysisParser] = None
    # check if Azure Document Intelligence credentials are provided
    if document_intelligence_service:
        credential: AsyncTokenCredential | AzureKeyCredential
        if document_intelligence_key:
            credential = AzureKeyCredential(document_intelligence_key)
        else:
            credential = azure_credential
        doc_int_parser = DocumentAnalysisParser(
            endpoint=f"https://{document_intelligence_service}.cognitiveservices.azure.com/",
            credential=credential,
            process_figures=process_figures,
        )

    pdf_parser: Optional[Parser] = None
    if use_local_pdf_parser or document_intelligence_service is None:
        pdf_parser = LocalPdfParser()
    elif doc_int_parser is not None:
        pdf_parser = doc_int_parser
    else:
        logger.warning("No PDF parser available")

    html_parser: Optional[Parser] = None
    if use_local_html_parser or document_intelligence_service is None:
        html_parser = LocalHTMLParser()
    elif doc_int_parser is not None:
        html_parser = doc_int_parser
    else:
        logger.warning("No HTML parser available")

    # These file formats can always be parsed:
    file_processors = {
        ".json": FileProcessor(JsonParser(), SimpleTextSplitter()),
        ".md": FileProcessor(TextParser(), sentence_text_splitter),
        ".txt": FileProcessor(TextParser(), sentence_text_splitter),
        ".csv": FileProcessor(CsvParser(), sentence_text_splitter),
    }
    # These require either a Python package or Document Intelligence
    if pdf_parser is not None:
        file_processors.update({".pdf": FileProcessor(pdf_parser, sentence_text_splitter)})
    if html_parser is not None:
        file_processors.update({".html": FileProcessor(html_parser, sentence_text_splitter)})
    # These file formats require Document Intelligence
    if doc_int_parser is not None:
        file_processors.update(
            {
                ".docx": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".pptx": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".xlsx": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".png": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".jpg": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".jpeg": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".tiff": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".bmp": FileProcessor(doc_int_parser, sentence_text_splitter),
                ".heic": FileProcessor(doc_int_parser, sentence_text_splitter),
            }
        )
    return file_processors


def select_processor_for_filename(file_name: str, file_processors: dict[str, FileProcessor]) -> FileProcessor:
    """Select the appropriate file processor for a given filename.

    Args:
        file_name: Name of the file to process
        file_processors: Dictionary mapping file extensions to FileProcessor instances

    Returns:
        FileProcessor instance for the file

    Raises:
        ValueError: If the file extension is not supported
    """
    file_ext = os.path.splitext(file_name)[1].lower()
    file_processor = file_processors.get(file_ext)
    if not file_processor:
        raise ValueError(f"Unsupported file type: {file_name}")
    return file_processor
