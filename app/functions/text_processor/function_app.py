"""Azure Function: Text Processor.

Processes markdown text into search chunks with (optional) embeddings and figure metadata.
"""

import io
import json
import logging
import os
from typing import Any

import azure.functions as func
from azure.identity.aio import ManagedIdentityCredential

from prepdocslib.blobmanager import BlobManager
from prepdocslib.listfilestrategy import File
from prepdocslib.page import ImageOnPage, Page
from prepdocslib.servicesetup import (
    OpenAIHost,
    setup_embeddings_service,
    setup_openai_client,
)
from prepdocslib.textprocessor import process_text
from prepdocslib.textsplitter import SentenceTextSplitter

# Mark the function as anonymous since we are protecting it with built-in auth instead
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger(__name__)

USE_VECTORS = os.getenv("USE_VECTORS", "true").lower() == "true"
USE_MULTIMODAL = os.getenv("USE_MULTIMODAL", "false").lower() == "true"

OPENAI_HOST = os.getenv("OPENAI_HOST", "azure")
AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE", "")
AZURE_OPENAI_CUSTOM_URL = os.getenv("AZURE_OPENAI_CUSTOM_URL", "")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "")
AZURE_OPENAI_EMB_MODEL_NAME = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-3-large")
AZURE_OPENAI_EMB_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "3072"))

SENTENCE_SPLITTER = SentenceTextSplitter()

# ---------------------------------------------------------------------------
# Global credential initialisation (single shared Managed Identity credential)
# ---------------------------------------------------------------------------
if AZURE_CLIENT_ID := (os.getenv("AZURE_CLIENT_ID") or os.getenv("IDENTITY_CLIENT_ID") or os.getenv("MSI_CLIENT_ID")):
    logger.info("Using Managed Identity with client ID: %s", AZURE_CLIENT_ID)
    GLOBAL_CREDENTIAL = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
else:
    logger.info("Using default Managed Identity without explicit client ID")
    GLOBAL_CREDENTIAL = ManagedIdentityCredential()

# ---------------------------------------------------------------------------
# Embedding service initialisation (optional)
# ---------------------------------------------------------------------------
EMBEDDING_SERVICE = None
if USE_VECTORS:
    embeddings_ready = (AZURE_OPENAI_SERVICE or AZURE_OPENAI_CUSTOM_URL) and (
        AZURE_OPENAI_EMB_DEPLOYMENT or AZURE_OPENAI_EMB_MODEL_NAME
    )
    if embeddings_ready:
        try:
            # Setup OpenAI client
            openai_host = OpenAIHost(OPENAI_HOST)
            openai_client, azure_openai_endpoint = setup_openai_client(
                openai_host=openai_host,
                azure_credential=GLOBAL_CREDENTIAL,
                azure_openai_service=AZURE_OPENAI_SERVICE or None,
                azure_openai_custom_url=AZURE_OPENAI_CUSTOM_URL or None,
            )

            # Setup embeddings service
            EMBEDDING_SERVICE = setup_embeddings_service(
                openai_host,
                openai_client,
                emb_model_name=AZURE_OPENAI_EMB_MODEL_NAME,
                emb_model_dimensions=AZURE_OPENAI_EMB_DIMENSIONS,
                azure_openai_deployment=AZURE_OPENAI_EMB_DEPLOYMENT or None,
                azure_openai_endpoint=azure_openai_endpoint,
            )
            logger.info(
                "Embedding service initialised (deployment=%s, model=%s, dims=%d)",
                AZURE_OPENAI_EMB_DEPLOYMENT or AZURE_OPENAI_EMB_MODEL_NAME,
                AZURE_OPENAI_EMB_MODEL_NAME,
                AZURE_OPENAI_EMB_DIMENSIONS,
            )
        except Exception as exc:  # pragma: no cover - defensive initialisation
            logger.error("Failed to initialise embedding service: %s", exc, exc_info=True)
            EMBEDDING_SERVICE = None
    else:
        logger.warning("USE_VECTORS is true but embedding configuration incomplete; embeddings disabled")


@app.function_name(name="process_text")
@app.route(route="process", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def process_text_entry(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Search custom skill entry point for chunking and embeddings."""

    try:
        payload = req.get_json()
    except ValueError as exc:
        logger.error("Invalid JSON payload: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON"}),
            mimetype="application/json",
            status_code=400,
        )

    values = payload.get("values", [])
    output_values: list[dict[str, Any]] = []

    for record in values:
        record_id = record.get("recordId", "")
        data = record.get("data", {})
        try:
            chunks = await _process_document(data)
            output_values.append(
                {
                    "recordId": record_id,
                    "data": {"chunks": chunks},
                    "errors": [],
                    "warnings": [],
                }
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to process record %s: %s", record_id, exc, exc_info=True)
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


async def _process_document(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Combine figures with page text, split into chunks, and (optionally) embed.

    Parameters
    ----------
    data: dict[str, Any]
        Skill payload containing consolidated_document with file metadata, pages, and figures.

    Returns
    -------
    list[dict[str, Any]]
        Chunk dictionaries ready for downstream indexing.
    """

    # Extract consolidated_document object from Shaper skill
    consolidated_doc = data.get("consolidated_document", data)

    file_name = consolidated_doc.get("file_name", "document")
    storage_url = consolidated_doc.get("storageUrl") or consolidated_doc.get("metadata_storage_path") or file_name
    pages_input = consolidated_doc.get("pages", [])  # [{page_num, text, figure_ids}]
    figures_input = consolidated_doc.get("figures", [])  # serialized skill payload

    # Merge enriched fields from figure processor into figures array
    # TODO: possibly remove enriched_*, are they actually needed?
    enriched_descriptions = data.get("enriched_descriptions", [])
    enriched_urls = data.get("enriched_urls", [])
    enriched_embeddings = data.get("enriched_embeddings", [])

    for i, figure in enumerate(figures_input):
        if i < len(enriched_descriptions):
            figure["description"] = enriched_descriptions[i]
        if i < len(enriched_urls):
            figure["url"] = enriched_urls[i]
        if i < len(enriched_embeddings):
            figure["embedding"] = enriched_embeddings[i]

    # Debug: log the first figure to see what fields are present
    if figures_input:
        logger.info("DEBUG: First figure keys after merge: %s", list(figures_input[0].keys()))
        logger.info(
            "DEBUG: First figure sample after merge: %s",
            {k: str(v)[:50] if v else v for k, v in list(figures_input[0].items())[:10]},
        )

    figures_by_id = {figure["figure_id"]: figure for figure in figures_input}

    logger.info("Processing %s: %d pages, %d figures", file_name, len(pages_input), len(figures_input))

    # Build Page objects with placeholders intact (figure markup will be injected by combine_text_with_figures())
    pages: list[Page] = []
    offset = 0
    for page_entry in pages_input:
        # Zero-based page numbering: pages emitted by extractor already zero-based
        page_num = int(page_entry.get("page_num", len(pages)))
        page_text = page_entry.get("text", "")
        page_obj = Page(page_num=page_num, offset=offset, text=page_text)
        offset += len(page_text)

        # Construct ImageOnPage objects from figureIds list
        figure_ids: list[str] = page_entry.get("figure_ids", [])
        for fid in figure_ids:
            figure_payload = figures_by_id.get(fid)
            if not figure_payload:
                logger.warning("Figure ID %s not found in figures metadata for page %d", fid, page_num)
                continue
            logger.info(
                "Deserializing figure %s: has description=%s, has url=%s, has bytes_base64=%s",
                fid,
                "description" in figure_payload,
                "url" in figure_payload,
                "bytes_base64" in figure_payload,
            )
            logger.info(
                "Figure %s payload values: description='%s', url='%s'",
                fid,
                figure_payload.get("description", "MISSING")[:100] if figure_payload.get("description") else "NONE",
                figure_payload.get("url", "MISSING")[:100] if figure_payload.get("url") else "NONE",
            )
            try:
                image_on_page, _ = ImageOnPage.from_skill_payload(figure_payload)
                logger.info(
                    "Figure %s deserialized: description='%s', url='%s', placeholder=%s",
                    fid,
                    (image_on_page.description or "NONE")[:100],
                    image_on_page.url or "NONE",
                    image_on_page.placeholder,
                )
                page_obj.images.append(image_on_page)
            except Exception as exc:
                logger.error("Failed to deserialize figure %s: %s", fid, exc, exc_info=True)
        pages.append(page_obj)

    if not pages:
        logger.info("No textual content found for %s", file_name)
        return []

    # Create a lightweight File wrapper required by process_text
    dummy_stream = io.BytesIO(b"")
    dummy_stream.name = file_name
    file_wrapper = File(content=dummy_stream)

    sections = process_text(pages, file_wrapper, SENTENCE_SPLITTER, category=None)
    if not sections:
        return []

    # Generate embeddings for section texts
    chunk_texts = [s.chunk.text for s in sections]
    embeddings: list[list[float]] | None = None
    if USE_VECTORS and chunk_texts:
        if EMBEDDING_SERVICE:
            embeddings = await EMBEDDING_SERVICE.create_embeddings(chunk_texts)
        else:
            logger.warning("Embeddings requested but service not initialised; skipping vectors")

    # Use the same id base generation as local ingestion pipeline for parity
    normalized_id = file_wrapper.filename_to_id()
    outputs: list[dict[str, Any]] = []
    for idx, section in enumerate(sections):
        content = section.chunk.text.strip()
        if not content:
            continue
        embedding_vec = embeddings[idx] if embeddings else None
        image_refs: list[dict[str, Any]] = []
        for image in section.chunk.images:
            ref = {
                "url": image.url or "",
                "description": image.description or "",
                "boundingbox": list(image.bbox),
            }
            if USE_MULTIMODAL and image.embedding is not None:
                ref["embedding"] = image.embedding
            image_refs.append(ref)
        chunk_entry: dict[str, Any] = {
            "id": f"{normalized_id}-{idx:04d}",
            "content": content,
            "sourcepage": BlobManager.sourcepage_from_file_page(file_name, section.chunk.page_num),
            "sourcefile": file_name,
            "parent_id": storage_url,
            **({"images": image_refs} if image_refs else {}),
        }

        if embedding_vec is not None:
            if len(embedding_vec) == AZURE_OPENAI_EMB_DIMENSIONS:
                chunk_entry["embedding"] = embedding_vec
            else:
                logger.warning(
                    "Skipping embedding for %s chunk %d due to dimension mismatch (expected %d, got %d)",
                    file_name,
                    idx,
                    AZURE_OPENAI_EMB_DIMENSIONS,
                    len(embedding_vec),
                )
        elif USE_VECTORS:
            logger.warning("Embeddings were requested but missing for %s chunk %d", file_name, idx)

        outputs.append(chunk_entry)

    return outputs
