import argparse
import asyncio
import logging
import os
from typing import Optional

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from openai import AsyncOpenAI
from rich.logging import RichHandler

from load_azd_env import load_azd_env
from prepdocslib.filestrategy import FileStrategy
from prepdocslib.integratedvectorizerstrategy import (
    IntegratedVectorizerStrategy,
)
from prepdocslib.listfilestrategy import (
    LocalListFileStrategy,
)
from prepdocslib.servicesetup import (
    OpenAIHost,
    build_file_processors,
    clean_key_if_exists,
    setup_blob_manager,
    setup_embeddings_service,
    setup_figure_processor,
    setup_image_embeddings_service,
    setup_openai_client,
    setup_search_info,
)
from prepdocslib.strategy import DocumentAction, Strategy

logger = logging.getLogger("scripts")


async def check_search_service_connectivity(search_service: str) -> bool:
    """Check if the search service is accessible by hitting the /ping endpoint."""
    ping_url = f"https://{search_service}.search.windows.net/ping"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
    except Exception as e:
        logger.debug(f"Search service ping failed: {e}")
        return False


def setup_list_file_strategy(
    azure_credential: AsyncTokenCredential,
    local_files: str,
    enable_global_documents: bool = False,
):
    logger.info("Using local files: %s", local_files)
    list_file_strategy = LocalListFileStrategy(
        path_pattern=local_files, enable_global_documents=enable_global_documents
    )
    return list_file_strategy


def setup_file_processors(
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: Optional[str],
    document_intelligence_key: Optional[str] = None,
    local_pdf_parser: bool = False,
    local_html_parser: bool = False,
    use_content_understanding: bool = False,
    use_multimodal: bool = False,
    openai_client: Optional[AsyncOpenAI] = None,
    openai_model: Optional[str] = None,
    openai_deployment: Optional[str] = None,
    content_understanding_endpoint: Optional[str] = None,
):
    """Setup file processors and figure processor for document ingestion.

    Uses build_file_processors from servicesetup to ensure consistent parser/splitter
    selection logic with the Azure Functions cloud ingestion pipeline.
    """
    file_processors = build_file_processors(
        azure_credential=azure_credential,
        document_intelligence_service=document_intelligence_service,
        document_intelligence_key=document_intelligence_key,
        use_local_pdf_parser=local_pdf_parser,
        use_local_html_parser=local_html_parser,
        process_figures=use_multimodal,
    )

    figure_processor = setup_figure_processor(
        credential=azure_credential,
        use_multimodal=use_multimodal,
        use_content_understanding=use_content_understanding,
        content_understanding_endpoint=content_understanding_endpoint,
        openai_client=openai_client,
        openai_model=openai_model,
        openai_deployment=openai_deployment,
    )

    return file_processors, figure_processor


async def main(strategy: Strategy, setup_index: bool = True):
    if setup_index:
        await strategy.setup()

    await strategy.run()


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Prepare documents by extracting content from PDFs, splitting content into sections, uploading to blob storage, and indexing in a search index."
    )
    parser.add_argument("files", nargs="?", help="Files to be processed")

    parser.add_argument(
        "--category", help="Value for the category field in the search index for all sections indexed in this run"
    )
    parser.add_argument(
        "--disablebatchvectors", action="store_true", help="Don't compute embeddings in batch for the sections"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove references to this document from blob storage and the search index",
    )
    parser.add_argument(
        "--removeall",
        action="store_true",
        help="Remove all blobs from blob storage and documents from the search index",
    )

    # Optional key specification:
    parser.add_argument(
        "--searchkey",
        required=False,
        help="Optional. Use this Azure AI Search account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--storagekey",
        required=False,
        help="Optional. Use this Azure Blob Storage account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--documentintelligencekey",
        required=False,
        help="Optional. Use this Azure Document Intelligence account key instead of the current user identity to login (use az login to set current user for Azure)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
        # We only set the level to INFO for our logger,
        # to avoid seeing the noisy INFO level logs from the Azure SDKs
        logger.setLevel(logging.DEBUG)

    load_azd_env()

    if os.getenv("USE_CLOUD_INGESTION", "").lower() == "true":
        logger.warning(
            "Cloud ingestion is enabled. Please use setup_cloud_ingestion.py instead of prepdocs.py. Exiting."
        )
        exit(0)

    if (
        os.getenv("AZURE_PUBLIC_NETWORK_ACCESS") == "Disabled"
        and os.getenv("AZURE_USE_VPN_GATEWAY", "").lower() != "true"
    ):
        logger.error("AZURE_PUBLIC_NETWORK_ACCESS is set to Disabled. Exiting.")
        exit(0)

    use_int_vectorization = os.getenv("USE_FEATURE_INT_VECTORIZATION", "").lower() == "true"
    use_multimodal = os.getenv("USE_MULTIMODAL", "").lower() == "true"
    use_acls = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    enforce_access_control = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    enable_global_documents = os.getenv("AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS", "").lower() == "true"
    dont_use_vectors = os.getenv("USE_VECTORS", "").lower() == "false"
    use_agentic_knowledgebase = os.getenv("USE_AGENTIC_KNOWLEDGEBASE", "").lower() == "true"
    use_content_understanding = os.getenv("USE_MEDIA_DESCRIBER_AZURE_CU", "").lower() == "true"
    use_web_source = os.getenv("USE_WEB_SOURCE", "").lower() == "true"
    use_sharepoint_source = os.getenv("USE_SHAREPOINT_SOURCE", "").lower() == "true"

    # Use the current user identity to connect to Azure services. See infra/main.bicep for role assignments.
    if tenant_id := os.getenv("AZURE_TENANT_ID"):
        logger.info("Connecting to Azure services using the azd credential for tenant %s", tenant_id)
        azd_credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        logger.info("Connecting to Azure services using the azd credential for home tenant")
        azd_credential = AzureDeveloperCliCredential(process_timeout=60)

    if args.removeall:
        document_action = DocumentAction.RemoveAll
    elif args.remove:
        document_action = DocumentAction.Remove
    else:
        document_action = DocumentAction.Add

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    OPENAI_HOST = OpenAIHost(os.environ["OPENAI_HOST"])
    # Check for incompatibility
    # if openai host is not azure
    if use_agentic_knowledgebase and OPENAI_HOST not in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        raise Exception("Agentic retrieval requires an Azure OpenAI chat completion service")

    search_info = setup_search_info(
        search_service=os.environ["AZURE_SEARCH_SERVICE"],
        index_name=os.environ["AZURE_SEARCH_INDEX"],
        use_agentic_knowledgebase=use_agentic_knowledgebase,
        knowledgebase_name=os.getenv("AZURE_SEARCH_KNOWLEDGEBASE_NAME"),
        azure_openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_openai_knowledgebase_deployment=os.getenv("AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT"),
        azure_openai_knowledgebase_model=os.getenv("AZURE_OPENAI_KNOWLEDGEBASE_MODEL"),
        azure_credential=azd_credential,
        search_key=clean_key_if_exists(args.searchkey),
        azure_vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
    )

    # Check search service connectivity
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    is_connected = loop.run_until_complete(check_search_service_connectivity(search_service))

    if not is_connected:
        if os.getenv("AZURE_USE_PRIVATE_ENDPOINT"):
            logger.error(
                "Unable to connect to Azure AI Search service, which indicates either a network issue or a misconfiguration. You have AZURE_USE_PRIVATE_ENDPOINT enabled. Perhaps you're not yet connected to the VPN? Download the VPN configuration from the Azure portal here: %s",
                os.getenv("AZURE_VPN_CONFIG_DOWNLOAD_LINK"),
            )
        else:
            logger.error(
                "Unable to connect to Azure AI Search service, which indicates either a network issue or a misconfiguration."
            )
        exit(1)

    blob_manager = setup_blob_manager(
        azure_credential=azd_credential,
        storage_account=os.environ["AZURE_STORAGE_ACCOUNT"],
        storage_container=os.environ["AZURE_STORAGE_CONTAINER"],
        storage_resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        storage_key=clean_key_if_exists(args.storagekey),
        image_storage_container=os.environ.get("AZURE_IMAGESTORAGE_CONTAINER"),  # Pass the image container
    )
    list_file_strategy = setup_list_file_strategy(
        azure_credential=azd_credential,
        local_files=args.files,
        enable_global_documents=enable_global_documents,
    )

    emb_model_dimensions = 1536
    if os.getenv("AZURE_OPENAI_EMB_DIMENSIONS"):
        emb_model_dimensions = int(os.environ["AZURE_OPENAI_EMB_DIMENSIONS"])

    openai_client, azure_openai_endpoint = setup_openai_client(
        openai_host=OPENAI_HOST,
        azure_credential=azd_credential,
        azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
        openai_api_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
        openai_organization=os.getenv("OPENAI_ORGANIZATION"),
    )
    openai_embeddings_service = None
    if not dont_use_vectors:
        openai_embeddings_service = setup_embeddings_service(
            OPENAI_HOST,
            openai_client,
            emb_model_name=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
            emb_model_dimensions=emb_model_dimensions,
            azure_openai_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
            azure_openai_endpoint=azure_openai_endpoint,
            disable_batch=args.disablebatchvectors,
        )

    ingestion_strategy: Strategy
    if use_int_vectorization:

        if not openai_embeddings_service or OPENAI_HOST not in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
            raise Exception("Integrated vectorization strategy requires an Azure OpenAI embeddings service")

        ingestion_strategy = IntegratedVectorizerStrategy(
            search_info=search_info,
            list_file_strategy=list_file_strategy,
            blob_manager=blob_manager,
            document_action=document_action,
            embeddings=openai_embeddings_service,
            search_field_name_embedding=os.environ["AZURE_SEARCH_FIELD_NAME_EMBEDDING"],
            subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
            search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
            use_acls=use_acls,
            category=args.category,
            enforce_access_control=enforce_access_control,
        )
    else:
        file_processors, figure_processor = setup_file_processors(
            azure_credential=azd_credential,
            document_intelligence_service=os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE"),
            document_intelligence_key=clean_key_if_exists(args.documentintelligencekey),
            local_pdf_parser=os.getenv("USE_LOCAL_PDF_PARSER") == "true",
            local_html_parser=os.getenv("USE_LOCAL_HTML_PARSER") == "true",
            use_content_understanding=use_content_understanding,
            use_multimodal=use_multimodal,
            content_understanding_endpoint=os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT"),
            openai_client=openai_client,
            openai_model=os.getenv("AZURE_OPENAI_CHATGPT_MODEL"),
            openai_deployment=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") if OPENAI_HOST == OpenAIHost.AZURE else None,
        )

        image_embeddings_service = setup_image_embeddings_service(
            azure_credential=azd_credential,
            vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
            use_multimodal=use_multimodal,
        )

        ingestion_strategy = FileStrategy(
            search_info=search_info,
            list_file_strategy=list_file_strategy,
            blob_manager=blob_manager,
            file_processors=file_processors,
            document_action=document_action,
            embeddings=openai_embeddings_service,
            image_embeddings=image_embeddings_service,
            search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
            # Default to the previous field names for backward compatibility
            search_field_name_embedding=os.getenv("AZURE_SEARCH_FIELD_NAME_EMBEDDING", "embedding"),
            use_acls=use_acls,
            category=args.category,
            figure_processor=figure_processor,
            enforce_access_control=enforce_access_control,
            use_web_source=use_web_source,
            use_sharepoint_source=use_sharepoint_source,
        )

    try:
        loop.run_until_complete(main(ingestion_strategy, setup_index=not args.remove and not args.removeall))
    finally:
        # Gracefully close any async clients/credentials to avoid noisy destructor warnings
        try:
            loop.run_until_complete(blob_manager.close_clients())
            loop.run_until_complete(openai_client.close())
            loop.run_until_complete(azd_credential.close())
        except Exception as e:
            logger.debug(f"Failed to close async clients cleanly: {e}")
        loop.close()
