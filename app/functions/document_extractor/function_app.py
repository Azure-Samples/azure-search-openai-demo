"""
Azure Function: Document Extractor
Custom skill for Azure AI Search that extracts and processes document content.
"""

import io
import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

import azure.functions as func
from azure.core.exceptions import HttpResponseError
from azure.identity.aio import ManagedIdentityCredential
from azure.storage.filedatalake.aio import DataLakeServiceClient

from prepdocslib.blobmanager import BlobManager
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.page import Page
from prepdocslib.servicesetup import (
    build_file_processors,
    select_processor_for_filename,
    setup_blob_manager,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger(__name__)


@dataclass
class GlobalSettings:
    file_processors: dict[str, FileProcessor]
    azure_credential: ManagedIdentityCredential
    blob_manager: BlobManager
    storage_is_adls: bool
    storage_account: str
    storage_container: str
    enable_global_document_access: bool
    data_lake_service_client: DataLakeServiceClient | None


settings: GlobalSettings | None = None


def configure_global_settings():
    global settings

    # Environment configuration
    use_local_pdf_parser = os.getenv("USE_LOCAL_PDF_PARSER", "false").lower() == "true"
    use_local_html_parser = os.getenv("USE_LOCAL_HTML_PARSER", "false").lower() == "true"
    use_multimodal = os.getenv("USE_MULTIMODAL", "false").lower() == "true"
    document_intelligence_service = os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE")
    storage_is_adls = os.getenv("USE_CLOUD_INGESTION_ACLS", "false").lower() == "true"
    enable_global_document_access = os.getenv("AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS", "false").lower() == "true"

    # Cloud ingestion storage account (ADLS Gen2 when ACLs enabled, standard blob otherwise)
    # Fallback to AZURE_STORAGE_ACCOUNT is for legacy deployments only - may be removed in future
    storage_account = os.getenv("AZURE_CLOUD_INGESTION_STORAGE_ACCOUNT") or os.environ["AZURE_STORAGE_ACCOUNT"]
    storage_container = os.environ["AZURE_STORAGE_CONTAINER"]

    # Single shared managed identity credential
    if AZURE_CLIENT_ID := os.getenv("AZURE_CLIENT_ID"):
        logger.info("Using Managed Identity with client ID: %s", AZURE_CLIENT_ID)
        azure_credential = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
    else:
        logger.info("Using default Managed Identity without client ID")
        azure_credential = ManagedIdentityCredential()

    # Build file processors dict for parser selection
    file_processors = build_file_processors(
        azure_credential=azure_credential,
        document_intelligence_service=document_intelligence_service,
        document_intelligence_key=None,
        use_local_pdf_parser=use_local_pdf_parser,
        use_local_html_parser=use_local_html_parser,
        process_figures=use_multimodal,
    )

    blob_manager = setup_blob_manager(
        azure_credential=azure_credential,
        storage_account=storage_account,
        storage_container=storage_container,
        storage_resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    )

    # Initialize ADLS client only if using ADLS Gen2 storage for ACL extraction
    data_lake_service_client = None
    if storage_is_adls:
        data_lake_service_client = DataLakeServiceClient(
            account_url=f"https://{storage_account}.dfs.core.windows.net",
            credential=azure_credential,
        )

    settings = GlobalSettings(
        file_processors=file_processors,
        azure_credential=azure_credential,
        blob_manager=blob_manager,
        storage_is_adls=storage_is_adls,
        storage_account=storage_account,
        storage_container=storage_container,
        enable_global_document_access=enable_global_document_access,
        data_lake_service_client=data_lake_service_client,
    )


@app.function_name(name="extract")
@app.route(route="extract", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def extract_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Search Custom Skill: Extract document content

    Input format (single record):
    {
        "values": [
            {
                "recordId": "1",
                "data": {
                    "metadata_storage_path": "https://<account>.blob.core.windows.net/<container>/<blob_path>"
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
    if settings is None:
        return func.HttpResponse(
            json.dumps({"error": "Settings not initialized"}),
            mimetype="application/json",
            status_code=500,
        )

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
            logger.error("Error processing record %s: %s", record_id, str(e), exc_info=True)
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
        logger.error("Fatal error in extract_document: %s", str(e), exc_info=True)
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)


async def process_document(data: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single document: download, parse, extract figures, upload images

    Args:
        data: Input data with metadata_storage_path

    Returns:
        Dictionary with 'text' (markdown) and 'images' (list of {url, description})
    """
    if settings is None:
        raise RuntimeError("Global settings not initialized")

    # Get blob path from metadata_storage_path URL
    # URL format: https://<account>.blob.core.windows.net/<container>/<blob_path>
    storage_path = data["metadata_storage_path"]
    parsed_url = urlparse(storage_path)
    # Path is /<container>/<blob_path>, so split and take everything after container
    path_parts = unquote(parsed_url.path).lstrip("/").split("/", 1)
    if len(path_parts) < 2:
        raise ValueError(f"Invalid storage path format: {storage_path}")
    blob_path_within_container = path_parts[1]  # Everything after the container name

    logger.info("Downloading blob: %s", blob_path_within_container)
    result = await settings.blob_manager.download_blob(blob_path_within_container)
    if result is None:
        raise ValueError(f"Blob not found: {blob_path_within_container}")

    document_bytes, properties = result
    document_stream = io.BytesIO(document_bytes)
    document_stream.name = blob_path_within_container

    logger.info("Processing document: %s", blob_path_within_container)

    # Get parser from file_processors dict based on file extension
    file_processor = select_processor_for_filename(blob_path_within_container, settings.file_processors)
    parser = file_processor.parser

    pages: list[Page] = []
    try:
        document_stream.seek(0)
        pages = [page async for page in parser.parse(content=document_stream)]
    except HttpResponseError as exc:
        raise ValueError(f"Parser failed for {blob_path_within_container}: {exc.message}") from exc
    finally:
        document_stream.close()

    # Extract ACLs if using ADLS Gen2 storage
    oids: list[str] = []
    groups: list[str] = []
    if settings.storage_is_adls:
        oids, groups = await get_file_acls(blob_path_within_container)

    components = build_document_components(blob_path_within_container, pages, oids, groups)
    return components


async def get_file_acls(file_path: str) -> tuple[list[str], list[str]]:
    """
    Extract user and group IDs from ADLS Gen2 ACLs for a file.

    Args:
        file_path: Path to the file within the container

    Returns:
        Tuple of (user_oids, group_ids) extracted from the file's ACLs.
        If the "other" ACL entry has read permission, returns (["all"], ["all"])
        to indicate global access for any authenticated user.
    """
    if settings is None:
        raise RuntimeError("Global settings not initialized")
    if settings.data_lake_service_client is None:
        raise RuntimeError("ADLS client not initialized - storage_is_adls may be false")

    oids: list[str] = []
    groups: list[str] = []
    other_has_read = False

    try:
        file_system_client = settings.data_lake_service_client.get_file_system_client(settings.storage_container)
        file_client = file_system_client.get_file_client(file_path)

        acl_props = await file_client.get_access_control(upn=False)
        acl_string = acl_props.get("acl", "")

        logger.info("Retrieved ACL for %s: %s", file_path, acl_string)

        # Parse ACL string format: "user::rwx,user:oid:rwx,group::r-x,group:gid:r-x,other::---"
        # https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control
        for entry in acl_string.split(","):
            parts = entry.split(":")
            if len(parts) != 3:
                continue
            scope_type = parts[0]
            identity = parts[1]
            permissions = parts[2]

            # Check if "other" has read permission - this means global access
            # The "other" entry has an empty identity: "other::r--" or "other::r-x"
            # https://github.com/hurtn/datalake-on-ADLS/blob/master/Understanding%20access%20control%20and%20data%20lake%20configurations%20in%20ADLS%20Gen2.md#option-2-the-other-acl-entry
            if scope_type == "other" and len(identity) == 0 and "r" in permissions:
                other_has_read = True
                continue

            # Only include if read permission is granted and identity is specified
            if len(identity) == 0:
                continue
            if scope_type == "user" and "r" in permissions:
                oids.append(identity)
            elif scope_type == "group" and "r" in permissions:
                groups.append(identity)

        # If "other" has read permission AND global access is enabled, document is globally accessible
        if other_has_read and settings.enable_global_document_access:
            logger.info(
                "File %s has 'other' read permission and global access enabled - setting global access", file_path
            )
            return ["all"], ["all"]
        elif other_has_read:
            logger.info(
                "File %s has 'other' read permission but AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS is not enabled",
                file_path,
            )

        logger.info("Extracted ACLs - oids: %s, groups: %s", oids, groups)

    except Exception as e:
        logger.warning("Failed to retrieve ACLs for %s: %s", file_path, str(e))
        # Return empty lists on failure - document will still be indexed but without ACLs

    return oids, groups


def build_document_components(
    file_name: str, pages: list[Page], oids: list[str] | None = None, groups: list[str] | None = None
) -> dict[str, Any]:
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
        "oids": oids or [],
        "groups": groups or [],
    }


# Initialize settings at module load time, unless we're in a test environment
if os.environ.get("PYTEST_CURRENT_TEST") is None:
    try:
        configure_global_settings()
    except KeyError as e:
        logger.warning("Could not initialize settings at module load time: %s", e)
