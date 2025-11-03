"""Shared service setup helpers for OpenAI and multimodal image embeddings.

This module centralizes logic that was previously duplicated between the local
ingestion script (`prepdocs.py`) and Azure Functions (e.g. `figure_processor`).

Functions exported:
    - setup_openai_client: Create an Async OpenAI / Azure OpenAI client using
      either key auth or passwordless (Managed Identity / Developer CLI).
    - setup_image_embeddings_service: Create an ImageEmbeddings helper when
      multimodal features are enabled.

The goal is to keep these concerns DRY so that credential / endpoint handling
stays consistent across ingestion pathways.
"""

from __future__ import annotations

import logging
import os
from enum import Enum

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from openai import AsyncAzureOpenAI, AsyncOpenAI

from .blobmanager import BlobManager
from .embeddings import ImageEmbeddings
from .figureprocessor import FigureProcessor, MediaDescriptionStrategy

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
    *,
    openai_host: OpenAIHost,
    azure_credential: AsyncTokenCredential,
    azure_openai_api_key: str | None = None,
    azure_openai_api_version: str | None = None,
    azure_openai_service: str | None = None,
    azure_openai_custom_url: str | None = None,
    azure_openai_chat_deployment: str | None = None,
    openai_api_key: str | None = None,
    openai_organization: str | None = None,
) -> AsyncOpenAI:
    """Create an Async OpenAI client for either Azure-hosted or public OpenAI API.

    For Azure, passwordless auth (Managed Identity / Developer CLI) is used
    unless an override API key is provided. A chat deployment name can be
    passed for convenience when downstream code requires it.
    """

    if openai_host not in OpenAIHost:
        raise ValueError(f"Invalid OPENAI_HOST value: {openai_host}.")

    if openai_host in (OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM):
        if openai_host == OpenAIHost.AZURE_CUSTOM:
            if not azure_openai_custom_url:
                raise ValueError("AZURE_OPENAI_CUSTOM_URL must be set for azure_custom host")
            endpoint = azure_openai_custom_url
        else:
            if not azure_openai_service:
                raise ValueError("AZURE_OPENAI_SERVICE must be set for azure host")
            endpoint = f"https://{azure_openai_service}.openai.azure.com"

        if azure_openai_api_key:
            logger.info("Using Azure OpenAI key override for client auth")
            return AsyncAzureOpenAI(
                api_version=azure_openai_api_version,
                azure_endpoint=endpoint,
                api_key=azure_openai_api_key,
                azure_deployment=azure_openai_chat_deployment,
            )
        logger.info("Using passwordless auth (token provider) for Azure OpenAI client")
        token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
        return AsyncAzureOpenAI(
            api_version=azure_openai_api_version,
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            azure_deployment=azure_openai_chat_deployment,
        )

    if openai_host == OpenAIHost.LOCAL:
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not base_url:
            raise ValueError("OPENAI_BASE_URL must be set when OPENAI_HOST=local")
        logger.info("Using local OpenAI-compatible endpoint: %s", base_url)
        return AsyncOpenAI(base_url=base_url, api_key="no-key-required")

    # Public OpenAI API
    if openai_api_key is None:
        raise ValueError("OPENAI_API_KEY is required for public OpenAI host")
    logger.info("Using public OpenAI host with key authentication")
    return AsyncOpenAI(api_key=openai_api_key, organization=openai_organization)


def setup_image_embeddings_service(
    *,
    azure_credential: AsyncTokenCredential,
    vision_endpoint: str | None,
    use_multimodal: bool,
) -> ImageEmbeddings | None:
    """Create an ImageEmbeddings helper if multimodal features are enabled.

    Returns None when multimodal is disabled so calling code can skip image
    embedding generation gracefully.
    """

    if not use_multimodal:
        logger.info("Multimodal disabled; not creating image embeddings service")
        return None
    if vision_endpoint is None:
        raise ValueError("An Azure AI Vision endpoint must be provided for multimodal features")

    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    logger.info("Creating ImageEmbeddings service for endpoint %s", vision_endpoint)
    return ImageEmbeddings(endpoint=vision_endpoint, token_provider=token_provider)


__all__ = [
    "OpenAIHost",
    "setup_openai_client",
    "setup_image_embeddings_service",
    "setup_blob_manager",
    "setup_figure_processor",
]


def setup_blob_manager(
    *,
    storage_account: str,
    storage_container: str,
    credential: AsyncTokenCredential | str,
    storage_resource_group: str | None = None,
    subscription_id: str | None = None,
    image_storage_container: str | None = None,
) -> BlobManager:
    """Create a BlobManager instance for document or figure storage.

    The optional resource group and subscription are retained for parity with
    local ingestion (used for diagnostic operations) but not required by
    Azure Functions. Image container may differ from the main document
    container when figures are stored separately.
    """
    endpoint = f"https://{storage_account}.blob.core.windows.net"
    return BlobManager(
        endpoint=endpoint,
        container=storage_container,
        account=storage_account,
        credential=credential,
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
