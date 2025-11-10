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
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .figureprocessor import FigureProcessor, MediaDescriptionStrategy
from .htmlparser import LocalHTMLParser
from .parser import Parser
from .pdfparser import DocumentAnalysisParser, LocalPdfParser
from .textparser import TextParser

logger = logging.getLogger("scripts")


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
            api_key=api_key_or_token,  # type: ignore[arg-type]
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


def select_parser(
    *,
    file_name: str,
    content_type: str,
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: str | None,
    document_intelligence_key: str | None = None,
    process_figures: bool = False,
    use_local_pdf_parser: bool = False,
    use_local_html_parser: bool = False,
) -> Parser:
    """Return a parser instance appropriate for the file type and configuration.

    Args:
        file_name: Source filename (used to derive extension)
        content_type: MIME type (fallback for extension-based selection)
        azure_credential: Token credential for DI service
        document_intelligence_service: Name of DI service (None disables DI)
        document_intelligence_key: Optional key credential (overrides token when provided)
        process_figures: Whether figure extraction should be enabled in DI parser
        use_local_pdf_parser: Force local PDF parsing instead of DI
        use_local_html_parser: Force local HTML parsing instead of DI

    Returns:
        Parser capable of yielding Page objects for the document.

    Raises:
        ValueError: Unsupported file type or missing DI configuration for required formats.
    """
    extension = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    ext_with_dot = f".{extension}" if extension else ""

    # Build DI parser lazily only if needed
    di_parser: DocumentAnalysisParser | None = None
    if document_intelligence_service:
        credential: AsyncTokenCredential | AzureKeyCredential
        if document_intelligence_key:
            credential = AzureKeyCredential(document_intelligence_key)
        else:
            credential = azure_credential
        di_parser = DocumentAnalysisParser(
            endpoint=f"https://{document_intelligence_service}.cognitiveservices.azure.com/",
            credential=credential,
            process_figures=process_figures,
        )

    # Plain text / structured text formats always local
    if ext_with_dot in {".txt", ".md", ".csv", ".json"} or content_type.startswith("text/plain"):
        return TextParser()

    # HTML
    if ext_with_dot in {".html", ".htm"} or content_type in {"text/html", "application/html"}:
        if use_local_html_parser or not di_parser:
            return LocalHTMLParser()
        return di_parser

    # PDF
    if ext_with_dot == ".pdf":
        if use_local_pdf_parser or not di_parser:
            return LocalPdfParser()
        return di_parser

    # Formats requiring DI
    di_required_exts = {".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".heic"}
    if ext_with_dot in di_required_exts:
        if not di_parser:
            raise ValueError("Document Intelligence service must be configured to process this file type")
        return di_parser

    # Fallback: if MIME suggests application/* and DI available, use DI
    if content_type.startswith("application/") and di_parser:
        return di_parser

    raise ValueError(f"Unsupported file type: {file_name}")
