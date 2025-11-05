"""
Azure Function: Document Extractor
Custom skill for Azure AI Search that extracts and processes document content.
"""

import base64
import io
import json
import logging
import os
from typing import Any

import azure.functions as func
from azure.core.exceptions import HttpResponseError
from azure.identity.aio import ManagedIdentityCredential

from prepdocslib.ingestionhelpers import select_parser
from prepdocslib.page import Page

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger(__name__)


USE_LOCAL_PDF_PARSER = os.getenv("USE_LOCAL_PDF_PARSER", "false").lower() == "true"
USE_LOCAL_HTML_PARSER = os.getenv("USE_LOCAL_HTML_PARSER", "false").lower() == "true"
USE_MULTIMODAL = os.getenv("USE_MULTIMODAL", "false").lower() == "true"

DOCUMENT_INTELLIGENCE_SERVICE = os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE")

# Eagerly create a single managed identity credential instance for the worker.
if AZURE_CLIENT_ID := os.getenv("AZURE_CLIENT_ID"):
    logger.info("Using Managed Identity with client ID: %s", AZURE_CLIENT_ID)
    AZURE_CREDENTIAL = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
else:
    logger.info("Using default Managed Identity without client ID")
    AZURE_CREDENTIAL = ManagedIdentityCredential()


@app.function_name(name="extract")
@app.route(route="extract", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def extract_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Search Custom Skill: Extract document content

    Input format (single record; file data only):
    # https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-document-intelligence-layout#skill-inputs
    {
        "values": [
            {
                "recordId": "1",
                "data": {
                    // Base64 encoded file (skillset must enable file data)
                    "file_data": {
                        "$type": "file",
                        "data": "base64..."
                    },
                    // Optional
                    "file_name": "doc.pdf"
                }
            }
        ]
    }

    Output format (snake_case only):
    {
        "values": [
            {
                "recordId": "1",
                "data": {
                    "pages": [
                        {"page_num": 0, "text": "Page 1 text", "figure_ids": ["fig1"]},
                        {"page_num": 1, "text": "Page 2 text", "figure_ids": []}
                    ],
                    "figures": [
                        {
                            "figure_id": "fig1",
                            "page_num": 0,
                            "document_file_name": "doc.pdf",
                            "filename": "fig1.png",
                            "mime_type": "image/png",
                            "bytes_base64": "...",
                            "bbox": [100,150,300,400],
                            "title": "Figure Title",
                            "placeholder": "<figure id=\"fig1\"></figure>"
                        }
                    ]
                },
                "errors": [],
                "warnings": []
            }
        ]
    }
    """
    try:
        # Parse custom skill input
        req_body = req.get_json()
        input_values = req_body.get("values", [])

        if len(input_values) != 1:
            raise ValueError("document_extractor expects exactly one record per request, set batchSize to 1.")

        input_record = input_values[0]
        record_id = input_record.get("recordId", "")
        data = input_record.get("data", {})

        try:
            result = await process_document(data)
            output_values = [
                {
                    "recordId": record_id,
                    "data": result,
                    "errors": [],
                    "warnings": [],
                }
            ]
        except Exception as e:
            logger.error(f"Error processing record {record_id}: {str(e)}", exc_info=True)
            output_values = [
                {
                    "recordId": record_id,
                    "data": {},
                    "errors": [{"message": str(e)}],
                    "warnings": [],
                }
            ]

        return func.HttpResponse(json.dumps({"values": output_values}), mimetype="application/json", status_code=200)

    except Exception as e:
        logger.error(f"Fatal error in extract_document: {str(e)}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)


async def process_document(data: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single document: download, parse, extract figures, upload images

    Args:
        data: Input data with blobUrl, fileName, contentType

    Returns:
        Dictionary with 'text' (markdown) and 'images' (list of {url, description})
    """
    document_stream, file_name, content_type = get_document_stream_filedata(data)
    logger.info("Processing document: %s", file_name)

    parser = select_parser(
        file_name=file_name,
        content_type=content_type,
        azure_credential=AZURE_CREDENTIAL,
        document_intelligence_service=DOCUMENT_INTELLIGENCE_SERVICE or None,
        document_intelligence_key=None,
        process_figures=USE_MULTIMODAL,
        use_local_pdf_parser=USE_LOCAL_PDF_PARSER,
        use_local_html_parser=USE_LOCAL_HTML_PARSER,
    )

    pages: list[Page] = []
    try:
        document_stream.seek(0)
        pages = [page async for page in parser.parse(content=document_stream)]
    except HttpResponseError as exc:
        raise ValueError(f"Parser failed for {file_name}: {exc.message}") from exc
    finally:
        document_stream.close()

    components = build_document_components(file_name, pages)
    return components


def get_document_stream_filedata(data: dict[str, Any]) -> tuple[io.BytesIO, str, str]:
    """Return a BytesIO stream for file_data input only (skillset must send file bytes)."""
    file_payload = data.get("file_data", {})
    encoded = file_payload.get("data")
    if not encoded:
        raise ValueError("file_data payload missing base64 data")
    document_bytes = base64.b64decode(encoded)
    file_name = data.get("file_name") or data.get("fileName") or file_payload.get("name") or "document"
    content_type = data.get("contentType") or file_payload.get("contentType") or "application/octet-stream"
    stream = io.BytesIO(document_bytes)
    stream.name = file_name
    return stream, file_name, content_type


def build_document_components(file_name: str, pages: list[Page]) -> dict[str, Any]:
    page_entries: list[dict[str, Any]] = []
    figure_entries: list[dict[str, Any]] = []

    for page in pages:
        page_text = page.text or ""
        figure_ids_on_page: list[str] = []
        if page.images:
            for image in page.images:
                figure_ids_on_page.append(image.figure_id)
                figure_entries.append(image.to_skill_payload(file_name))

        page_entries.append(
            {
                "page_num": page.page_num,
                "text": page_text,
                "figure_ids": figure_ids_on_page,
            }
        )

    return {
        "file_name": file_name,
        "pages": page_entries,
        "figures": figure_entries,
    }
