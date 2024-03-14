import argparse
import asyncio
import logging
from typing import Optional, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential, get_bearer_token_provider
from azure.keyvault.secrets.aio import SecretClient

from prepdocslib.blobmanager import BlobManager
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

logger = logging.getLogger("ingester")


def clean_key_if_exists(key: Union[str, None]) -> Union[str, None]:
    """Remove leading and trailing whitespace from a key if it exists. If the key is empty, return None."""
    if key is not None and key.strip() != "":
        return key.strip()
    return None


async def setup_search_info(
    search_service: str,
    index_name: str,
    azure_credential: AsyncTokenCredential,
    search_key: Union[str, None] = None,
    key_vault_name: Union[str, None] = None,
    search_secret_name: Union[str, None] = None,
) -> SearchInfo:
    if key_vault_name and search_secret_name:
        async with SecretClient(
            vault_url=f"https://{key_vault_name}.vault.azure.net", credential=azure_credential
        ) as key_vault_client:
            search_key = (await key_vault_client.get_secret(search_secret_name)).value  # type: ignore[attr-defined]

    search_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
        azure_credential if search_key is None else AzureKeyCredential(search_key)
    )

    return SearchInfo(
        endpoint=f"https://{search_service}.search.windows.net/",
        credential=search_creds,
        index_name=index_name,
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
    openai_service: str,
    openai_deployment: str,
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
            open_ai_deployment=openai_deployment,
            open_ai_model_name=openai_model_name,
            credential=azure_open_ai_credential,
            disable_batch=disable_batch_vectors,
        )
    else:
        if openai_key is None:
            raise ValueError("OpenAI key is required when using the non-Azure OpenAI API")
        return OpenAIEmbeddingService(
            open_ai_model_name=openai_model_name,
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
):
    html_parser: Parser
    pdf_parser: Parser
    doc_int_parser: DocumentAnalysisParser

    # check if Azure Document Intelligence credentials are provided
    if document_intelligence_service is not None:
        documentintelligence_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
            azure_credential if document_intelligence_key is None else AzureKeyCredential(document_intelligence_key)
        )
        doc_int_parser = DocumentAnalysisParser(
            endpoint=f"https://{document_intelligence_service}.cognitiveservices.azure.com/",
            credential=documentintelligence_creds,
        )
    if local_pdf_parser or document_intelligence_service is None:
        pdf_parser = LocalPdfParser()
    else:
        pdf_parser = doc_int_parser
    if local_html_parser or document_intelligence_service is None:
        html_parser = LocalHTMLParser()
    else:
        html_parser = doc_int_parser
    sentence_text_splitter = SentenceTextSplitter(has_image_embeddings=search_images)
    return {
        ".pdf": FileProcessor(pdf_parser, sentence_text_splitter),
        ".html": FileProcessor(html_parser, sentence_text_splitter),
        ".json": FileProcessor(JsonParser(), SimpleTextSplitter()),
        ".docx": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".pptx": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".xlsx": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".png": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".jpg": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".jpeg": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".tiff": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".bmp": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".heic": FileProcessor(doc_int_parser, sentence_text_splitter),
        ".md": FileProcessor(TextParser(), sentence_text_splitter),
        ".txt": FileProcessor(TextParser(), sentence_text_splitter),
    }


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
        description="Prepare documents by extracting content from PDFs, splitting content into sections, uploading to blob storage, and indexing in a search index.",
        epilog="Example: prepdocs.py '..\data\*' --storageaccount myaccount --container mycontainer --searchservice mysearch --index myindex -v",
    )
    parser.add_argument("files", nargs="?", help="Files to be processed")
    parser.add_argument(
        "--datalakestorageaccount", required=False, help="Optional. Azure Data Lake Storage Gen2 Account name"
    )
    parser.add_argument(
        "--datalakefilesystem",
        required=False,
        default="gptkbcontainer",
        help="Optional. Azure Data Lake Storage Gen2 filesystem name",
    )
    parser.add_argument(
        "--datalakepath",
        required=False,
        help="Optional. Azure Data Lake Storage Gen2 filesystem path containing files to index. If omitted, index the entire filesystem",
    )
    parser.add_argument(
        "--datalakekey", required=False, help="Optional. Use this key when authenticating to Azure Data Lake Gen2"
    )
    parser.add_argument(
        "--useacls", action="store_true", help="Store ACLs from Azure Data Lake Gen2 Filesystem in the search index"
    )
    parser.add_argument(
        "--category", help="Value for the category field in the search index for all sections indexed in this run"
    )
    parser.add_argument(
        "--skipblobs", action="store_true", help="Skip uploading individual pages to Azure Blob Storage"
    )
    parser.add_argument("--storageaccount", help="Azure Blob Storage account name")
    parser.add_argument("--container", help="Azure Blob Storage container name")
    parser.add_argument("--storageresourcegroup", help="Azure blob storage resource group")
    parser.add_argument(
        "--storagekey",
        required=False,
        help="Optional. Use this Azure Blob Storage account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--tenantid", required=False, help="Optional. Use this to define the Azure directory where to authenticate)"
    )
    parser.add_argument(
        "--subscriptionid",
        required=False,
        help="Optional. Use this to define managed identity connection string in integrated vectorization",
    )
    parser.add_argument(
        "--searchservice",
        help="Name of the Azure AI Search service where content should be indexed (must exist already)",
    )
    parser.add_argument(
        "--searchserviceassignedid",
        required=False,
        help="Search service system assigned Identity (Managed identity) (used for integrated vectorization)",
    )
    parser.add_argument(
        "--index",
        help="Name of the Azure AI Search index where content should be indexed (will be created if it doesn't exist)",
    )
    parser.add_argument(
        "--searchkey",
        required=False,
        help="Optional. Use this Azure AI Search account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--searchsecretname",
        required=False,
        help="Required if searchkey is not provided and search service is free sku. Fetch the Azure AI Vision key from this keyvault instead of the instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--searchanalyzername",
        required=False,
        default="en.microsoft",
        help="Optional. Name of the Azure AI Search analyzer to use for the content field in the index",
    )
    parser.add_argument("--openaihost", help="Host of the API used to compute embeddings ('azure' or 'openai')")
    parser.add_argument("--openaiservice", help="Name of the Azure OpenAI service used to compute embeddings")
    parser.add_argument(
        "--openaideployment",
        help="Name of the Azure OpenAI model deployment for an embedding model ('text-embedding-ada-002' recommended)",
    )
    parser.add_argument(
        "--openaimodelname", help="Name of the Azure OpenAI embedding model ('text-embedding-ada-002' recommended)"
    )
    parser.add_argument(
        "--novectors",
        action="store_true",
        help="Don't compute embeddings for the sections (e.g. don't call the OpenAI embeddings API during indexing)",
    )
    parser.add_argument(
        "--disablebatchvectors", action="store_true", help="Don't compute embeddings in batch for the sections"
    )
    parser.add_argument(
        "--openaikey",
        required=False,
        help="Optional. Use this Azure OpenAI account key instead of the current user identity to login (use az login to set current user for Azure). This is required only when using non-Azure endpoints.",
    )
    parser.add_argument("--openaiorg", required=False, help="This is required only when using non-Azure endpoints.")
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
    parser.add_argument(
        "--localpdfparser",
        action="store_true",
        help="Use PyPdf local PDF parser (supports only digital PDFs) instead of Azure Document Intelligence service to extract text, tables and layout from the documents",
    )
    parser.add_argument(
        "--localhtmlparser",
        action="store_true",
        help="Use Beautiful soap local HTML parser instead of Azure Document Intelligence service to extract text, tables and layout from the documents",
    )
    parser.add_argument(
        "--documentintelligenceservice",
        required=False,
        help="Optional. Name of the Azure Document Intelligence service which will be used to extract text, tables and layout from the documents (must exist already)",
    )
    parser.add_argument(
        "--documentintelligencekey",
        required=False,
        help="Optional. Use this Azure Document Intelligence account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--searchimages",
        action="store_true",
        required=False,
        help="Optional. Generate image embeddings to enable each page to be searched as an image",
    )
    parser.add_argument(
        "--visionendpoint",
        required=False,
        help="Optional, required if --searchimages is specified. Endpoint of Azure AI Vision service to use when embedding images.",
    )
    parser.add_argument(
        "--keyvaultname",
        required=False,
        help="Required only if any keys must be fetched from the key vault.",
    )
    parser.add_argument(
        "--useintvectorization",
        required=False,
        help="Required if --useintvectorization is specified. Enable Integrated vectorizer indexer support which is in preview)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(message)s")
        # We only set the level to INFO for our logger,
        # to avoid seeing the noisy INFO level logs from the Azure SDKs
        logger.setLevel(logging.INFO)

    use_int_vectorization = args.useintvectorization and args.useintvectorization.lower() == "true"

    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = (
        AzureDeveloperCliCredential()
        if args.tenantid is None
        else AzureDeveloperCliCredential(tenant_id=args.tenantid, process_timeout=60)
    )

    if args.removeall:
        document_action = DocumentAction.RemoveAll
    elif args.remove:
        document_action = DocumentAction.Remove
    else:
        document_action = DocumentAction.Add

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    search_info = loop.run_until_complete(
        setup_search_info(
            search_service=args.searchservice,
            index_name=args.index,
            azure_credential=azd_credential,
            search_key=clean_key_if_exists(args.searchkey),
            key_vault_name=args.keyvaultname,
            search_secret_name=args.searchsecretname,
        )
    )
    blob_manager = setup_blob_manager(
        azure_credential=azd_credential,
        storage_account=args.storageaccount,
        storage_container=args.container,
        storage_resource_group=args.storageresourcegroup,
        subscription_id=args.subscriptionid,
        search_images=args.searchimages,
        storage_key=clean_key_if_exists(args.storagekey),
    )
    list_file_strategy = setup_list_file_strategy(
        azure_credential=azd_credential,
        local_files=args.files,
        datalake_storage_account=args.datalakestorageaccount,
        datalake_filesystem=args.datalakefilesystem,
        datalake_path=args.datalakepath,
        datalake_key=clean_key_if_exists(args.datalakekey),
    )
    openai_embeddings_service = setup_embeddings_service(
        azure_credential=azd_credential,
        openai_host=args.openaihost,
        openai_model_name=args.openaimodelname,
        openai_service=args.openaiservice,
        openai_deployment=args.openaideployment,
        openai_key=clean_key_if_exists(args.openaikey),
        openai_org=args.openaiorg,
        disable_vectors=args.novectors,
        disable_batch_vectors=args.disablebatchvectors,
    )

    ingestion_strategy: Strategy
    if use_int_vectorization:
        ingestion_strategy = IntegratedVectorizerStrategy(
            search_info=search_info,
            list_file_strategy=list_file_strategy,
            blob_manager=blob_manager,
            document_action=document_action,
            embeddings=openai_embeddings_service,
            subscription_id=args.subscriptionid,
            search_service_user_assigned_id=args.searchserviceassignedid,
            search_analyzer_name=args.searchanalyzername,
            use_acls=args.useacls,
            category=args.category,
        )
    else:
        file_processors = setup_file_processors(
            azure_credential=azd_credential,
            document_intelligence_service=args.documentintelligenceservice,
            document_intelligence_key=clean_key_if_exists(args.documentintelligencekey),
            local_pdf_parser=args.localpdfparser,
            local_html_parser=args.localhtmlparser,
            search_images=args.searchimages,
        )
        image_embeddings_service = setup_image_embeddings_service(
            azure_credential=azd_credential, vision_endpoint=args.visionendpoint, search_images=args.searchimages
        )

        ingestion_strategy = FileStrategy(
            search_info=search_info,
            list_file_strategy=list_file_strategy,
            blob_manager=blob_manager,
            file_processors=file_processors,
            document_action=document_action,
            embeddings=openai_embeddings_service,
            image_embeddings=image_embeddings_service,
            search_analyzer_name=args.searchanalyzername,
            use_acls=args.useacls,
            category=args.category,
        )

    loop.run_until_complete(main(ingestion_strategy, setup_index=not args.remove and not args.removeall))
    loop.close()
