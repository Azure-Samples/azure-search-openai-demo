"""
Azure Function: Figure Processor
Custom skill for Azure AI Search that enriches figure payloads emitted by the document extractor.

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
from typing import Any

import azure.functions as func
from azure.identity.aio import ManagedIdentityCredential, get_bearer_token_provider

from prepdocslib.blobmanager import BlobManager
from prepdocslib.embeddings import ImageEmbeddings
from prepdocslib.figureprocessor import FigureProcessor, process_page_image
from prepdocslib.page import ImageOnPage
from prepdocslib.servicesetup import (
    OpenAIHost,
    setup_blob_manager,
    setup_figure_processor,
    setup_openai_client,
)

# Mark the function as anonymous since we are protecting it with built-in auth instead
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger(__name__)

# Environment configuration
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "")
IMAGE_CONTAINER = os.getenv("AZURE_IMAGESTORAGE_CONTAINER") or os.getenv("AZURE_STORAGE_CONTAINER", "")
USE_MULTIMODAL = os.getenv("USE_MULTIMODAL", "false").lower() == "true"
USE_MEDIA_DESCRIBER_AZURE_CU = os.getenv("USE_MEDIA_DESCRIBER_AZURE_CU", "false").lower() == "true"
CONTENT_UNDERSTANDING_ENDPOINT = os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT", "")
AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE", "")
AZURE_OPENAI_CUSTOM_URL = os.getenv("AZURE_OPENAI_CUSTOM_URL", "")
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "")
AZURE_OPENAI_CHATGPT_MODEL = os.getenv("AZURE_OPENAI_CHATGPT_MODEL", "")
AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT", "")

BLOB_MANAGER: BlobManager | None
FIGURE_PROCESSOR: FigureProcessor | None
IMAGE_EMBEDDINGS: ImageEmbeddings | None

# Single shared managed identity credential (matches document_extractor pattern)
if AZURE_CLIENT_ID := os.getenv("AZURE_CLIENT_ID"):
    logger.info("Using Managed Identity with client ID: %s", AZURE_CLIENT_ID)
    GLOBAL_CREDENTIAL = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
else:
    logger.info("Using default Managed Identity without client ID")
    GLOBAL_CREDENTIAL = ManagedIdentityCredential()


# Direct eager initialization (no helper functions)
# Blob Manager
if AZURE_STORAGE_ACCOUNT and IMAGE_CONTAINER:
    BLOB_MANAGER = setup_blob_manager(
        storage_account=AZURE_STORAGE_ACCOUNT,
        storage_container=IMAGE_CONTAINER,
        azure_credential=GLOBAL_CREDENTIAL,
        image_storage_container=IMAGE_CONTAINER,
    )
else:
    logger.warning("Blob manager not initialized due to missing storage configuration")
    BLOB_MANAGER = None

# Figure Processor
_openai_client = None
_openai_model = None
_openai_deployment = None
openai_ready = USE_MULTIMODAL and (AZURE_OPENAI_SERVICE or AZURE_OPENAI_CUSTOM_URL) and AZURE_OPENAI_CHATGPT_DEPLOYMENT
if openai_ready:
    _host = OpenAIHost.AZURE_CUSTOM if AZURE_OPENAI_CUSTOM_URL else OpenAIHost.AZURE
    _openai_client, _ = setup_openai_client(
        openai_host=_host,
        azure_credential=GLOBAL_CREDENTIAL,
        azure_openai_service=AZURE_OPENAI_SERVICE or None,
        azure_openai_custom_url=AZURE_OPENAI_CUSTOM_URL or None,
    )
    _openai_model = AZURE_OPENAI_CHATGPT_MODEL or AZURE_OPENAI_CHATGPT_DEPLOYMENT
    _openai_deployment = AZURE_OPENAI_CHATGPT_DEPLOYMENT
elif USE_MULTIMODAL:
    logger.warning("USE_MULTIMODAL is true but Azure OpenAI configuration incomplete; disabling OPENAI strategy")

FIGURE_PROCESSOR = setup_figure_processor(
    credential=GLOBAL_CREDENTIAL,
    use_multimodal=bool(openai_ready),
    use_content_understanding=USE_MEDIA_DESCRIBER_AZURE_CU,
    content_understanding_endpoint=CONTENT_UNDERSTANDING_ENDPOINT or None,
    openai_client=_openai_client,
    openai_model=_openai_model,
    openai_deployment=_openai_deployment,
)

# Image Embeddings
if USE_MULTIMODAL and AZURE_VISION_ENDPOINT:
    _token_provider = get_bearer_token_provider(GLOBAL_CREDENTIAL, "https://cognitiveservices.azure.com/.default")
    IMAGE_EMBEDDINGS = ImageEmbeddings(AZURE_VISION_ENDPOINT, _token_provider)
else:
    IMAGE_EMBEDDINGS = None


@app.function_name(name="process_figure")
@app.route(route="process", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def process_figure_request(req: func.HttpRequest) -> func.HttpResponse:
    """Entrypoint for Azure Search custom skill calls."""

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
            logger.info(
                "Figure processor input for %s: url=%s, description=%s",
                image_on_page.figure_id,
                image_on_page.url,
                image_on_page.description,
            )
            await process_page_image(
                image=image_on_page,
                document_filename=file_name,
                blob_manager=BLOB_MANAGER,
                image_embeddings_client=IMAGE_EMBEDDINGS,
                figure_processor=FIGURE_PROCESSOR,
            )
            logger.info(
                "Figure processor after enrichment for %s: url=%s, description=%s",
                image_on_page.figure_id,
                (image_on_page.url or "NONE")[:100],
                (image_on_page.description or "NONE")[:100],
            )
            figure_payload = image_on_page.to_skill_payload(file_name, include_bytes_base64=False, include_bytes=False)
            logger.info(
                "Figure processor returning payload for %s: url='%s', description='%s'",
                image_on_page.figure_id,
                figure_payload.get("url", "MISSING")[:100] if figure_payload.get("url") else "NONE",
                figure_payload.get("description", "MISSING")[:100] if figure_payload.get("description") else "NONE",
            )
            output_values.append(
                {
                    "recordId": record_id,
                    "data": figure_payload,
                    "errors": [],
                    "warnings": [],
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
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
