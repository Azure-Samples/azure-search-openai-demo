import argparse
import asyncio
import logging
import os
from typing import Union

import aiohttp
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from openai import AsyncOpenAI
from rich.logging import RichHandler

from load_azd_env import load_azd_env
from prepdocslib.cloudingestionstrategy import CloudIngestionStrategy
from prepdocslib.csvparser import CsvParser
from prepdocslib.embeddings import AzureOpenAIEmbeddingService, OpenAIEmbeddingService
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy
from prepdocslib.ingestionhelpers import select_parser
from prepdocslib.integratedvectorizerstrategy import (
    IntegratedVectorizerStrategy,
)
from prepdocslib.jsonparser import JsonParser
from prepdocslib.listfilestrategy import (
    ADLSGen2ListFileStrategy,
    ListFileStrategy,
    LocalListFileStrategy,
)
from prepdocslib.parser import Parser
from prepdocslib.servicesetup import (
    OpenAIHost,
    setup_blob_manager,
    setup_figure_processor,
    setup_image_embeddings_service,
    setup_openai_client,
)

# Removed direct pdf parser imports (selection now via select_parser)
from prepdocslib.strategy import DocumentAction, SearchInfo, Strategy
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SentenceTextSplitter, SimpleTextSplitter

logger = logging.getLogger("scripts")


def clean_key_if_exists(key: Union[str, None]) -> Union[str, None]:
    """Remove leading and trailing whitespace from a key if it exists. If the key is empty, return None."""
    if key is not None and key.strip() != "":
        return key.strip()
    return None


def require_env_var(name: str) -> str:
    """Fetch an environment variable or raise a helpful error if it is missing."""

    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable {name} must be set to use cloud ingestion.")
    return value


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


async def setup_search_info(
    search_service: str,
    index_name: str,
    azure_credential: AsyncTokenCredential,
    use_agentic_retrieval: Union[bool, None] = None,
    azure_openai_endpoint: Union[str, None] = None,
    agent_name: Union[str, None] = None,
    agent_max_output_tokens: Union[int, None] = None,
    azure_openai_searchagent_deployment: Union[str, None] = None,
    azure_openai_searchagent_model: Union[str, None] = None,
    search_key: Union[str, None] = None,
    azure_vision_endpoint: Union[str, None] = None,
) -> SearchInfo:
    search_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
        azure_credential if search_key is None else AzureKeyCredential(search_key)
    )
    if use_agentic_retrieval and azure_openai_searchagent_model is None:
        raise ValueError("Azure OpenAI SearchAgent model must be specified when using agentic retrieval.")

    return SearchInfo(
        endpoint=f"https://{search_service}.search.windows.net/",
        credential=search_creds,
        index_name=index_name,
        agent_name=agent_name,
        agent_max_output_tokens=agent_max_output_tokens,
        use_agentic_retrieval=use_agentic_retrieval,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_searchagent_model=azure_openai_searchagent_model,
        azure_openai_searchagent_deployment=azure_openai_searchagent_deployment,
        azure_vision_endpoint=azure_vision_endpoint,
    )


def setup_list_file_strategy(
    azure_credential: AsyncTokenCredential,
    local_files: Union[str, None],
    datalake_storage_account: Union[str, None],
    datalake_filesystem: Union[str, None],
    datalake_path: Union[str, None],
    datalake_key: Union[str, None],
    enable_global_documents: bool = False,
):
    list_file_strategy: ListFileStrategy
    if datalake_storage_account:
        if datalake_filesystem is None or datalake_path is None:
            raise ValueError("DataLake file system and path are required when using Azure Data Lake Gen2")
        adls_gen2_creds: Union[AsyncTokenCredential, str] = azure_credential if datalake_key is None else datalake_key
        logger.info("Using Data Lake Gen2 Storage Account: %s", datalake_storage_account)
        list_file_strategy = ADLSGen2ListFileStrategy(
            data_lake_storage_account=datalake_storage_account,
            data_lake_filesystem=datalake_filesystem,
            data_lake_path=datalake_path,
            credential=adls_gen2_creds,
            enable_global_documents=enable_global_documents,
        )
    elif local_files:
        logger.info("Using local files: %s", local_files)
        list_file_strategy = LocalListFileStrategy(
            path_pattern=local_files, enable_global_documents=enable_global_documents
        )
    else:
        raise ValueError("Either local_files or datalake_storage_account must be provided.")
    return list_file_strategy


def setup_embeddings_service(
    azure_credential: AsyncTokenCredential,
    openai_host: OpenAIHost,
    emb_model_name: str,
    emb_model_dimensions: int,
    azure_openai_service: Union[str, None],
    azure_openai_custom_url: Union[str, None],
    azure_openai_deployment: Union[str, None],
    azure_openai_key: Union[str, None],
    azure_openai_api_version: str,
    openai_key: Union[str, None],
    openai_org: Union[str, None],
    disable_vectors: bool = False,
    disable_batch_vectors: bool = False,
):
    if disable_vectors:
        logger.info("Not setting up embeddings service")
        return None

    if openai_host in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        azure_open_ai_credential: Union[AsyncTokenCredential, AzureKeyCredential] = (
            azure_credential if azure_openai_key is None else AzureKeyCredential(azure_openai_key)
        )
        return AzureOpenAIEmbeddingService(
            open_ai_service=azure_openai_service,
            open_ai_custom_url=azure_openai_custom_url,
            open_ai_deployment=azure_openai_deployment,
            open_ai_model_name=emb_model_name,
            open_ai_dimensions=emb_model_dimensions,
            open_ai_api_version=azure_openai_api_version,
            credential=azure_open_ai_credential,
            disable_batch=disable_batch_vectors,
        )
    else:
        if openai_key is None:
            raise ValueError("OpenAI key is required when using the non-Azure OpenAI API")
        return OpenAIEmbeddingService(
            open_ai_model_name=emb_model_name,
            open_ai_dimensions=emb_model_dimensions,
            credential=openai_key,
            organization=openai_org,
            disable_batch=disable_batch_vectors,
        )


def setup_file_processors(
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: Union[str, None],
    document_intelligence_key: Union[str, None] = None,
    local_pdf_parser: bool = False,
    local_html_parser: bool = False,
    use_content_understanding: bool = False,
    use_multimodal: bool = False,
    openai_client: Union[AsyncOpenAI, None] = None,
    openai_model: Union[str, None] = None,
    openai_deployment: Union[str, None] = None,
    content_understanding_endpoint: Union[str, None] = None,
):
    sentence_text_splitter = SentenceTextSplitter()

    # Build mapping of file extensions to parsers using shared select_parser helper.
    # Each select attempt may instantiate a DI parser; duplication is acceptable at startup.
    def _try_select(ext: str, content_type: str) -> Parser | None:
        file_name = f"dummy{ext}"
        try:
            return select_parser(
                file_name=file_name,
                content_type=content_type,
                azure_credential=azure_credential,
                document_intelligence_service=document_intelligence_service,
                document_intelligence_key=document_intelligence_key,
                process_figures=use_multimodal,
                use_local_pdf_parser=local_pdf_parser,
                use_local_html_parser=local_html_parser,
            )
        except ValueError:
            return None

    pdf_parser: Parser | None = _try_select(".pdf", "application/pdf")
    html_parser: Parser | None = _try_select(".html", "text/html")

    # DI-only formats
    di_exts = [
        ".docx",
        ".pptx",
        ".xlsx",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".heic",
    ]
    di_parsers: dict[str, Parser] = {}
    for ext in di_exts:
        parser = _try_select(ext, "application/octet-stream")
        if parser is not None:
            di_parsers[ext] = parser

    # These file formats can always be parsed:
    file_processors = {
        ".json": FileProcessor(JsonParser(), SimpleTextSplitter()),
        ".md": FileProcessor(TextParser(), sentence_text_splitter),
        ".txt": FileProcessor(TextParser(), sentence_text_splitter),
        ".csv": FileProcessor(CsvParser(), sentence_text_splitter),
    }
    # These require either a Python package or Document Intelligence
    if pdf_parser is not None:
        file_processors[".pdf"] = FileProcessor(pdf_parser, sentence_text_splitter)
    if html_parser is not None:
        file_processors[".html"] = FileProcessor(html_parser, sentence_text_splitter)
    for ext, parser in di_parsers.items():
        file_processors[ext] = FileProcessor(parser, sentence_text_splitter)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare documents by extracting content from PDFs, splitting content into sections, uploading to blob storage, and indexing in a search index."
    )
    parser.add_argument("files", nargs="?", help="Files to be processed")

    parser.add_argument(
        "--category", help="Value for the category field in the search index for all sections indexed in this run"
    )
    parser.add_argument(
        "--skipblobs", action="store_true", help="Skip uploading individual pages to Azure Blob Storage"
    )
    parser.add_argument(
        "--disablebatchvectors", action="store_true", help="Don't compute embeddings in batch for the sections"
    )
    parser.add_argument(
        "--use-cloud-ingestion",
        action="store_true",
        help="Use Azure AI Search indexer with cloud-hosted custom skills instead of local ingestion",
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
        "--datalakekey", required=False, help="Optional. Use this key when authenticating to Azure Data Lake Gen2"
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
    use_cloud_ingestion = args.use_cloud_ingestion or os.getenv("USE_CLOUD_INGESTION", "").lower() == "true"
    dont_use_vectors = os.getenv("USE_VECTORS", "").lower() == "false"
    use_agentic_retrieval = os.getenv("USE_AGENTIC_RETRIEVAL", "").lower() == "true"
    use_content_understanding = os.getenv("USE_MEDIA_DESCRIBER_AZURE_CU", "").lower() == "true"

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
    if use_agentic_retrieval and OPENAI_HOST not in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        raise Exception("Agentic retrieval requires an Azure OpenAI chat completion service")

    search_info = loop.run_until_complete(
        setup_search_info(
            search_service=os.environ["AZURE_SEARCH_SERVICE"],
            index_name=os.environ["AZURE_SEARCH_INDEX"],
            use_agentic_retrieval=use_agentic_retrieval,
            agent_name=os.getenv("AZURE_SEARCH_AGENT"),
            agent_max_output_tokens=int(os.getenv("AZURE_SEARCH_AGENT_MAX_OUTPUT_TOKENS", 10000)),
            azure_openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_openai_searchagent_deployment=os.getenv("AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT"),
            azure_openai_searchagent_model=os.getenv("AZURE_OPENAI_SEARCHAGENT_MODEL"),
            azure_credential=azd_credential,
            search_key=clean_key_if_exists(args.searchkey),
            azure_vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
        )
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
        datalake_storage_account=os.getenv("AZURE_ADLS_GEN2_STORAGE_ACCOUNT"),
        datalake_filesystem=os.getenv("AZURE_ADLS_GEN2_FILESYSTEM"),
        datalake_path=os.getenv("AZURE_ADLS_GEN2_FILESYSTEM_PATH"),
        datalake_key=clean_key_if_exists(args.datalakekey),
        enable_global_documents=enable_global_documents,
    )

    # https://learn.microsoft.com/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
    azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "2024-06-01"
    emb_model_dimensions = 1536
    if os.getenv("AZURE_OPENAI_EMB_DIMENSIONS"):
        emb_model_dimensions = int(os.environ["AZURE_OPENAI_EMB_DIMENSIONS"])
    openai_embeddings_service = setup_embeddings_service(
        azure_credential=azd_credential,
        openai_host=OPENAI_HOST,
        emb_model_name=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
        emb_model_dimensions=emb_model_dimensions,
        azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
        azure_openai_api_version=azure_openai_api_version,
        azure_openai_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
        openai_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
        openai_org=os.getenv("OPENAI_ORGANIZATION"),
        disable_vectors=dont_use_vectors,
        disable_batch_vectors=args.disablebatchvectors,
    )
    openai_client = setup_openai_client(
        openai_host=OPENAI_HOST,
        azure_credential=azd_credential,
        azure_openai_api_version=azure_openai_api_version,
        azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
        openai_api_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
        openai_organization=os.getenv("OPENAI_ORGANIZATION"),
    )

    ingestion_strategy: Strategy
    if use_cloud_ingestion:
        if args.category:
            logger.warning("Category assignment is not currently supported with cloud ingestion; ignoring.")
        if dont_use_vectors:
            raise ValueError("USE_VECTORS must remain true when using cloud ingestion.")
        if not openai_embeddings_service or not isinstance(openai_embeddings_service, AzureOpenAIEmbeddingService):
            raise ValueError("Cloud ingestion requires Azure OpenAI embeddings to configure the search index.")

        document_extractor_uri = require_env_var("DOCUMENT_EXTRACTOR_SKILL_ENDPOINT")
        document_extractor_resource_id = require_env_var("DOCUMENT_EXTRACTOR_SKILL_RESOURCE_ID")
        figure_processor_uri = require_env_var("FIGURE_PROCESSOR_SKILL_ENDPOINT")
        figure_processor_resource_id = require_env_var("FIGURE_PROCESSOR_SKILL_RESOURCE_ID")
        text_processor_uri = require_env_var("TEXT_PROCESSOR_SKILL_ENDPOINT")
        text_processor_resource_id = require_env_var("TEXT_PROCESSOR_SKILL_RESOURCE_ID")
        search_embedding_field = require_env_var("AZURE_SEARCH_FIELD_NAME_EMBEDDING")

        ingestion_strategy = CloudIngestionStrategy(
            list_file_strategy=list_file_strategy,
            blob_manager=blob_manager,
            search_info=search_info,
            embeddings=openai_embeddings_service,
            search_field_name_embedding=search_embedding_field,
            document_extractor_uri=document_extractor_uri,
            document_extractor_auth_resource_id=document_extractor_resource_id,
            figure_processor_uri=figure_processor_uri,
            figure_processor_auth_resource_id=figure_processor_resource_id,
            text_processor_uri=text_processor_uri,
            text_processor_auth_resource_id=text_processor_resource_id,
            subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
            document_action=document_action,
            search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
            use_acls=use_acls,
            use_multimodal=use_multimodal,
            enforce_access_control=enforce_access_control,
        )
    elif use_int_vectorization:

        if not openai_embeddings_service or not isinstance(openai_embeddings_service, AzureOpenAIEmbeddingService):
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
