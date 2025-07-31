import argparse
import asyncio
import logging
import os
from typing import Optional, Union

import aiohttp
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential, get_bearer_token_provider
from rich.logging import RichHandler

from load_azd_env import load_azd_env
from prepdocslib.blobmanager import BlobManager
from prepdocslib.csvparser import CsvParser
from prepdocslib.embeddings import (
    AzureOpenAIEmbeddingService,
    ImageEmbeddings,
    OpenAIEmbeddingService,
)
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy
from prepdocslib.htmlparser import LocalHTMLParser
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
from prepdocslib.pdfparser import DocumentAnalysisParser, LocalPdfParser
from prepdocslib.strategy import DocumentAction, SearchInfo, Strategy
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SentenceTextSplitter, SimpleTextSplitter

logger = logging.getLogger("scripts")


def clean_key_if_exists(key: Union[str, None]) -> Union[str, None]:
    """Remove leading and trailing whitespace from a key if it exists. If the key is empty, return None."""
    if key is not None and key.strip() != "":
        return key.strip()
    return None


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
    )


def setup_blob_manager(
    azure_credential: AsyncTokenCredential,
    storage_account: str,
    storage_container: str,
    storage_resource_group: str,
    subscription_id: str,
    search_images: bool,
    storage_key: Union[str, None] = None,
):
    storage_creds: Union[AsyncTokenCredential, str] = azure_credential if storage_key is None else storage_key
    return BlobManager(
        endpoint=f"https://{storage_account}.blob.core.windows.net",
        container=storage_container,
        account=storage_account,
        credential=storage_creds,
        resourceGroup=storage_resource_group,
        subscriptionId=subscription_id,
        store_page_images=search_images,
    )


def setup_list_file_strategy(
    azure_credential: AsyncTokenCredential,
    local_files: Union[str, None],
    datalake_storage_account: Union[str, None],
    datalake_filesystem: Union[str, None],
    datalake_path: Union[str, None],
    datalake_key: Union[str, None],
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
        )
    elif local_files:
        logger.info("Using local files: %s", local_files)
        list_file_strategy = LocalListFileStrategy(path_pattern=local_files)
    else:
        raise ValueError("Either local_files or datalake_storage_account must be provided.")
    return list_file_strategy


def setup_embeddings_service(
    azure_credential: AsyncTokenCredential,
    openai_host: str,
    openai_model_name: str,
    openai_service: Union[str, None],
    openai_custom_url: Union[str, None],
    openai_deployment: Union[str, None],
    openai_dimensions: int,
    openai_api_version: str,
    openai_key: Union[str, None],
    openai_org: Union[str, None],
    disable_vectors: bool = False,
    disable_batch_vectors: bool = False,
):
    if disable_vectors:
        logger.info("Not setting up embeddings service")
        return None

    if openai_host != "openai":
        azure_open_ai_credential: Union[AsyncTokenCredential, AzureKeyCredential] = (
            azure_credential if openai_key is None else AzureKeyCredential(openai_key)
        )
        return AzureOpenAIEmbeddingService(
            open_ai_service=openai_service,
            open_ai_custom_url=openai_custom_url,
            open_ai_deployment=openai_deployment,
            open_ai_model_name=openai_model_name,
            open_ai_dimensions=openai_dimensions,
            open_ai_api_version=openai_api_version,
            credential=azure_open_ai_credential,
            disable_batch=disable_batch_vectors,
        )
    else:
        if openai_key is None:
            raise ValueError("OpenAI key is required when using the non-Azure OpenAI API")
        return OpenAIEmbeddingService(
            open_ai_model_name=openai_model_name,
            open_ai_dimensions=openai_dimensions,
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
    search_images: bool = False,
    use_content_understanding: bool = False,
    content_understanding_endpoint: Union[str, None] = None,
):
    sentence_text_splitter = SentenceTextSplitter()

    doc_int_parser: Optional[DocumentAnalysisParser] = None
    # check if Azure Document Intelligence credentials are provided
    if document_intelligence_service is not None:
        documentintelligence_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
            azure_credential if document_intelligence_key is None else AzureKeyCredential(document_intelligence_key)
        )
        doc_int_parser = DocumentAnalysisParser(
            endpoint=f"https://{document_intelligence_service}.cognitiveservices.azure.com/",
            credential=documentintelligence_creds,
            use_content_understanding=use_content_understanding,
            content_understanding_endpoint=content_understanding_endpoint,
        )

    pdf_parser: Optional[Parser] = None
    if local_pdf_parser or document_intelligence_service is None:
        pdf_parser = LocalPdfParser()
    elif document_intelligence_service is not None:
        pdf_parser = doc_int_parser
    else:
        logger.warning("No PDF parser available")

    html_parser: Optional[Parser] = None
    if local_html_parser or document_intelligence_service is None:
        html_parser = LocalHTMLParser()
    elif document_intelligence_service is not None:
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


def setup_image_embeddings_service(
    azure_credential: AsyncTokenCredential, vision_endpoint: Union[str, None], search_images: bool
) -> Union[ImageEmbeddings, None]:
    image_embeddings_service: Optional[ImageEmbeddings] = None
    if search_images:
        if vision_endpoint is None:
            raise ValueError("A computer vision endpoint is required when GPT-4-vision is enabled.")
        image_embeddings_service = ImageEmbeddings(
            endpoint=vision_endpoint,
            token_provider=get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default"),
        )
    return image_embeddings_service


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
    parser.add_argument(
        "--searchserviceassignedid",
        required=False,
        help="Search service system assigned Identity (Managed identity) (used for integrated vectorization)",
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
    use_gptvision = os.getenv("USE_GPT4V", "").lower() == "true"
    use_acls = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL") is not None
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

    openai_host = os.environ["OPENAI_HOST"]
    # Check for incompatibility
    # if openai host is not azure
    if openai_host != "azure" and use_agentic_retrieval:
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
        search_images=use_gptvision,
        storage_key=clean_key_if_exists(args.storagekey),
    )
    list_file_strategy = setup_list_file_strategy(
        azure_credential=azd_credential,
        local_files=args.files,
        datalake_storage_account=os.getenv("AZURE_ADLS_GEN2_STORAGE_ACCOUNT"),
        datalake_filesystem=os.getenv("AZURE_ADLS_GEN2_FILESYSTEM"),
        datalake_path=os.getenv("AZURE_ADLS_GEN2_FILESYSTEM_PATH"),
        datalake_key=clean_key_if_exists(args.datalakekey),
    )

    openai_host = os.environ["OPENAI_HOST"]
    openai_key = None
    if os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"):
        openai_key = os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE")
    elif not openai_host.startswith("azure") and os.getenv("OPENAI_API_KEY"):
        openai_key = os.getenv("OPENAI_API_KEY")

    openai_dimensions = 1536
    if os.getenv("AZURE_OPENAI_EMB_DIMENSIONS"):
        openai_dimensions = int(os.environ["AZURE_OPENAI_EMB_DIMENSIONS"])
    openai_embeddings_service = setup_embeddings_service(
        azure_credential=azd_credential,
        openai_host=openai_host,
        openai_model_name=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
        openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        openai_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
        # https://learn.microsoft.com/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "2024-06-01",
        openai_dimensions=openai_dimensions,
        openai_key=clean_key_if_exists(openai_key),
        openai_org=os.getenv("OPENAI_ORGANIZATION"),
        disable_vectors=dont_use_vectors,
        disable_batch_vectors=args.disablebatchvectors,
    )

    ingestion_strategy: Strategy
    if use_int_vectorization:

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
            search_service_user_assigned_id=args.searchserviceassignedid,
            search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
            use_acls=use_acls,
            category=args.category,
        )
    else:
        file_processors = setup_file_processors(
            azure_credential=azd_credential,
            document_intelligence_service=os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE"),
            document_intelligence_key=clean_key_if_exists(args.documentintelligencekey),
            local_pdf_parser=os.getenv("USE_LOCAL_PDF_PARSER") == "true",
            local_html_parser=os.getenv("USE_LOCAL_HTML_PARSER") == "true",
            search_images=use_gptvision,
            use_content_understanding=use_content_understanding,
            content_understanding_endpoint=os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT"),
        )
        image_embeddings_service = setup_image_embeddings_service(
            azure_credential=azd_credential,
            vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
            search_images=use_gptvision,
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
            use_content_understanding=use_content_understanding,
            content_understanding_endpoint=os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT"),
        )

    loop.run_until_complete(main(ingestion_strategy, setup_index=not args.remove and not args.removeall))
    loop.close()
