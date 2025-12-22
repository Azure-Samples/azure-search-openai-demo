"""
Azure Function: Figure Processor
Custom skill for Azure AI Search that enriches figure payloads emitted by the document extractor.

This function is part of the standalone ingestion module and uses internal
imports instead of prepdocslib.

This function:
1. Accepts raw figure bytes and metadata (one record per request due to skill fanout).
2. Uploads rendered figure images to blob storage with citation overlays.
3. Generates natural-language captions via Azure OpenAI or Content Understanding (when configured).
4. Optionally computes image embeddings using Azure AI Vision (when multimodal is enabled).
5. Returns enriched figure metadata back to the indexer for downstream text processing.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import azure.functions as func
from azure.identity.aio import ManagedIdentityCredential, get_bearer_token_provider

# Import from the standalone ingestion module
from ingestion.storage.blob import BlobManager
from ingestion.embeddings.image import ImageEmbeddings
from ingestion.figures import FigureProcessor, MediaDescriptionStrategy
from ingestion.figures.processor import process_page_image
from ingestion.models import ImageOnPage
from ingestion.config import OpenAIHost

# Mark the function as anonymous since we are protecting it with built-in auth instead
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger(__name__)


@dataclass
class GlobalSettings:
    blob_manager: BlobManager
    figure_processor: FigureProcessor | None
    image_embeddings: ImageEmbeddings | None


settings: GlobalSettings | None = None


def setup_openai_client(
    openai_host: OpenAIHost,
    azure_credential: ManagedIdentityCredential,
    azure_openai_service: str | None,
    azure_openai_custom_url: str | None,
):
    """Set up OpenAI client for figure descriptions."""
    from openai import AsyncAzureOpenAI

    if openai_host == OpenAIHost.AZURE_CUSTOM and azure_openai_custom_url:
        azure_endpoint = azure_openai_custom_url
    elif azure_openai_service:
        azure_endpoint = f"https://{azure_openai_service}.openai.azure.com"
    else:
        raise ValueError("Azure OpenAI service or custom URL required")

    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    client = AsyncAzureOpenAI(
        api_version="2024-06-01",
        azure_endpoint=azure_endpoint,
        azure_ad_token_provider=token_provider,
    )
    return client, azure_endpoint


def configure_global_settings():
    global settings

    # Environment configuration
    # Required variables
    AZURE_STORAGE_ACCOUNT = os.environ["AZURE_STORAGE_ACCOUNT"]
    IMAGE_CONTAINER = os.environ["AZURE_IMAGESTORAGE_CONTAINER"]

    # Optional feature flags
    USE_MULTIMODAL = os.getenv("USE_MULTIMODAL", "false").lower() == "true"
    USE_MEDIA_DESCRIBER_AZURE_CU = os.getenv("USE_MEDIA_DESCRIBER_AZURE_CU", "false").lower() == "true"

    # Conditionally required (based on feature flags)
    CONTENT_UNDERSTANDING_ENDPOINT = os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT")
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_CUSTOM_URL = os.getenv("AZURE_OPENAI_CUSTOM_URL")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    AZURE_OPENAI_CHATGPT_MODEL = os.getenv("AZURE_OPENAI_CHATGPT_MODEL")
    AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT")

    # Single shared managed identity credential (matches document_extractor pattern)
    if AZURE_CLIENT_ID := os.getenv("AZURE_CLIENT_ID"):
        logger.info("Using Managed Identity with client ID: %s", AZURE_CLIENT_ID)
        AZURE_CREDENTIAL = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
    else:
        logger.info("Using default Managed Identity without client ID")
        AZURE_CREDENTIAL = ManagedIdentityCredential()

    # Blob Manager for image storage
    blob_manager = BlobManager(
        endpoint=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
        container=IMAGE_CONTAINER,
        credential=AZURE_CREDENTIAL,
        account=AZURE_STORAGE_ACCOUNT,
        image_container=IMAGE_CONTAINER,
    )

    # Figure Processor (with optional OpenAI for multimodal)
    openai_client = None
    openai_model = None
    openai_deployment = None
    if USE_MULTIMODAL and (AZURE_OPENAI_SERVICE or AZURE_OPENAI_CUSTOM_URL) and AZURE_OPENAI_CHATGPT_DEPLOYMENT:
        openai_client, _ = setup_openai_client(
            openai_host=OpenAIHost.AZURE_CUSTOM if AZURE_OPENAI_CUSTOM_URL else OpenAIHost.AZURE,
            azure_credential=AZURE_CREDENTIAL,
            azure_openai_service=AZURE_OPENAI_SERVICE,
            azure_openai_custom_url=AZURE_OPENAI_CUSTOM_URL,
        )
        openai_model = AZURE_OPENAI_CHATGPT_MODEL or AZURE_OPENAI_CHATGPT_DEPLOYMENT
        openai_deployment = AZURE_OPENAI_CHATGPT_DEPLOYMENT
    elif USE_MULTIMODAL and not USE_MEDIA_DESCRIBER_AZURE_CU:
        logger.warning(
            "USE_MULTIMODAL is true but Azure OpenAI configuration incomplete and Content Understanding not enabled"
        )

    # Determine media description strategy
    if not USE_MULTIMODAL:
        figure_processor = None
    elif USE_MEDIA_DESCRIBER_AZURE_CU and CONTENT_UNDERSTANDING_ENDPOINT:
        figure_processor = FigureProcessor(
            credential=AZURE_CREDENTIAL,
            strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
            content_understanding_endpoint=CONTENT_UNDERSTANDING_ENDPOINT,
        )
    elif openai_client and openai_model:
        figure_processor = FigureProcessor(
            credential=AZURE_CREDENTIAL,
            strategy=MediaDescriptionStrategy.OPENAI,
            openai_client=openai_client,
            openai_model=openai_model,
            openai_deployment=openai_deployment,
        )
    else:
        figure_processor = FigureProcessor(
            credential=AZURE_CREDENTIAL,
            strategy=MediaDescriptionStrategy.NONE,
        )

    # Image Embeddings (optional)
    if USE_MULTIMODAL and AZURE_VISION_ENDPOINT:
        token_provider = get_bearer_token_provider(AZURE_CREDENTIAL, "https://cognitiveservices.azure.com/.default")
        image_embeddings = ImageEmbeddings(AZURE_VISION_ENDPOINT, token_provider)
    else:
        image_embeddings = None

    settings = GlobalSettings(
        blob_manager=blob_manager,
        figure_processor=figure_processor,
        image_embeddings=image_embeddings,
    )


@app.function_name(name="process_figure")
@app.route(route="process", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def process_figure_request(req: func.HttpRequest) -> func.HttpResponse:
    """Entrypoint for Azure Search custom skill calls."""

    if settings is None:
        return func.HttpResponse(
            json.dumps({"error": "Settings not initialized"}),
            mimetype="application/json",
            status_code=500,
        )

    try:
        payload = req.get_json()
    except ValueError as exc:
        logger.error("Failed to parse request body: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON payload"}),
            mimetype="application/json",
            status_code=400,
        )

    input_values = payload.get("values", [])
    output_values: list[dict[str, Any]] = []

    for record in input_values:
        record_id = record.get("recordId", "")
        data = record.get("data", {})
        try:
            image_on_page, file_name = ImageOnPage.from_skill_payload(data)
            await process_page_image(
                image=image_on_page,
                document_filename=file_name,
                blob_manager=settings.blob_manager,
                image_embeddings_client=settings.image_embeddings,
                figure_processor=settings.figure_processor,
            )
            figure_payload = image_on_page.to_skill_payload(file_name, include_bytes_base64=False)
            output_values.append(
                {
                    "recordId": record_id,
                    "data": figure_payload,
                    "errors": [],
                    "warnings": [],
                }
            )
        except Exception as exc:
            logger.error("Error processing figure %s: %s", record_id, exc, exc_info=True)
            output_values.append(
                {
                    "recordId": record_id,
                    "data": {},
                    "errors": [{"message": str(exc)}],
                    "warnings": [],
                }
            )

    return func.HttpResponse(
        json.dumps({"values": output_values}),
        mimetype="application/json",
        status_code=200,
    )


# Initialize settings at module load time, unless we're in a test environment
if os.environ.get("PYTEST_CURRENT_TEST") is None:
    try:
        configure_global_settings()
    except KeyError as e:
        logger.warning("Could not initialize settings at module load time: %s", e)
