import argparse
import asyncio
from typing import Any, Optional, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from azure.keyvault.secrets.aio import SecretClient

from prepdocslib.blobmanager import BlobManager
from prepdocslib.embeddings import (
    AzureOpenAIEmbeddingService,
    ImageEmbeddings,
    OpenAIEmbeddings,
    OpenAIEmbeddingService,
)
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy
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
from prepdocslib.textsplitter import SentenceTextSplitter, SimpleTextSplitter


def is_key_empty(key):
    return key is None or len(key.strip()) == 0


async def get_vision_key(credential: AsyncTokenCredential) -> Optional[str]:
    if args.visionkey:
        return args.visionkey

    if args.keyvaultname and args.visionsecretname:
        key_vault_client = SecretClient(vault_url=f"https://{args.keyvaultname}.vault.azure.net", credential=credential)
        visionkey = await key_vault_client.get_secret(args.visionsecretname)
        return visionkey.value
    else:
        print("Error: Please provide --visionkey or --keyvaultname and --visionsecretname when using --searchimages.")
        exit(1)


async def setup_file_strategy(credential: AsyncTokenCredential, args: Any) -> Strategy:
    storage_creds = credential if is_key_empty(args.storagekey) else args.storagekey
    blob_manager = BlobManager(
        endpoint=f"https://{args.storageaccount}.blob.core.windows.net",
        container=args.container,
        account=args.storageaccount,
        credential=storage_creds,
        resourceGroup=args.storageresourcegroup,
        subscriptionId=args.subscriptionid,
        store_page_images=args.searchimages,
        verbose=args.verbose,
    )

    pdf_parser: Parser
    doc_int_parser: DocumentAnalysisParser

    # check if Azure Document Intelligence credentials are provided
    if args.documentintelligenceservice is not None:
        documentintelligence_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
            credential
            if is_key_empty(args.documentintelligencekey)
            else AzureKeyCredential(args.documentintelligencekey)
        )
        doc_int_parser = DocumentAnalysisParser(
            endpoint=f"https://{args.documentintelligenceservice}.cognitiveservices.azure.com/",
            credential=documentintelligence_creds,
            verbose=args.verbose,
        )
    if args.localpdfparser or args.documentintelligenceservice is None:
        pdf_parser = LocalPdfParser()
    else:
        pdf_parser = doc_int_parser
    sentence_text_splitter = SentenceTextSplitter(has_image_embeddings=args.searchimages)
    file_processors = {
        ".pdf": FileProcessor(pdf_parser, sentence_text_splitter),
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
    }
    use_vectors = not args.novectors
    embeddings: Optional[OpenAIEmbeddings] = None
    if use_vectors and args.openaihost != "openai":
        azure_open_ai_credential: Union[AsyncTokenCredential, AzureKeyCredential] = (
            credential if is_key_empty(args.openaikey) else AzureKeyCredential(args.openaikey)
        )
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service=args.openaiservice,
            open_ai_deployment=args.openaideployment,
            open_ai_model_name=args.openaimodelname,
            credential=azure_open_ai_credential,
            disable_batch=args.disablebatchvectors,
            verbose=args.verbose,
        )
    elif use_vectors:
        embeddings = OpenAIEmbeddingService(
            open_ai_model_name=args.openaimodelname,
            credential=args.openaikey,
            organization=args.openaiorg,
            disable_batch=args.disablebatchvectors,
            verbose=args.verbose,
        )

    image_embeddings: Optional[ImageEmbeddings] = None

    if args.searchimages:
        key = await get_vision_key(credential)
        image_embeddings = (
            ImageEmbeddings(credential=key, endpoint=args.visionendpoint, verbose=args.verbose) if key else None
        )

    print("Processing files...")
    list_file_strategy: ListFileStrategy
    if args.datalakestorageaccount:
        adls_gen2_creds = credential if is_key_empty(args.datalakekey) else args.datalakekey
        print(f"Using Data Lake Gen2 Storage Account {args.datalakestorageaccount}")
        list_file_strategy = ADLSGen2ListFileStrategy(
            data_lake_storage_account=args.datalakestorageaccount,
            data_lake_filesystem=args.datalakefilesystem,
            data_lake_path=args.datalakepath,
            credential=adls_gen2_creds,
            verbose=args.verbose,
        )
    else:
        print(f"Using local files in {args.files}")
        list_file_strategy = LocalListFileStrategy(path_pattern=args.files, verbose=args.verbose)

    if args.removeall:
        document_action = DocumentAction.RemoveAll
    elif args.remove:
        document_action = DocumentAction.Remove
    else:
        document_action = DocumentAction.Add

    return FileStrategy(
        list_file_strategy=list_file_strategy,
        blob_manager=blob_manager,
        file_processors=file_processors,
        document_action=document_action,
        embeddings=embeddings,
        image_embeddings=image_embeddings,
        search_analyzer_name=args.searchanalyzername,
        use_acls=args.useacls,
        category=args.category,
    )


async def setup_intvectorizer_strategy(credential: AsyncTokenCredential, args: Any) -> Strategy:
    storage_creds = credential if is_key_empty(args.storagekey) else args.storagekey
    blob_manager = BlobManager(
        endpoint=f"https://{args.storageaccount}.blob.core.windows.net",
        container=args.container,
        account=args.storageaccount,
        credential=storage_creds,
        resourceGroup=args.storageresourcegroup,
        subscriptionId=args.subscriptionid,
        store_page_images=args.searchimages,
        verbose=args.verbose,
    )

    use_vectors = not args.novectors
    embeddings: Union[AzureOpenAIEmbeddingService, None] = None
    if use_vectors and args.openaihost != "openai":
        azure_open_ai_credential: Union[AsyncTokenCredential, AzureKeyCredential] = (
            credential if is_key_empty(args.openaikey) else AzureKeyCredential(args.openaikey)
        )
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service=args.openaiservice,
            open_ai_deployment=args.openaideployment,
            open_ai_model_name=args.openaimodelname,
            credential=azure_open_ai_credential,
            disable_batch=args.disablebatchvectors,
            verbose=args.verbose,
        )

    print("Processing files...")
    list_file_strategy: ListFileStrategy
    if args.datalakestorageaccount:
        adls_gen2_creds = credential if is_key_empty(args.datalakekey) else args.datalakekey
        print(f"Using Data Lake Gen2 Storage Account {args.datalakestorageaccount}")
        list_file_strategy = ADLSGen2ListFileStrategy(
            data_lake_storage_account=args.datalakestorageaccount,
            data_lake_filesystem=args.datalakefilesystem,
            data_lake_path=args.datalakepath,
            credential=adls_gen2_creds,
            verbose=args.verbose,
        )
    else:
        print(f"Using local files in {args.files}")
        list_file_strategy = LocalListFileStrategy(path_pattern=args.files, verbose=args.verbose)

    if args.removeall:
        document_action = DocumentAction.RemoveAll
    elif args.remove:
        document_action = DocumentAction.Remove
    else:
        document_action = DocumentAction.Add

    return IntegratedVectorizerStrategy(
        list_file_strategy=list_file_strategy,
        blob_manager=blob_manager,
        document_action=document_action,
        embeddings=embeddings,
        subscription_id=args.subscriptionid,
        search_service_user_assigned_id=args.searchserviceassignedid,
        search_analyzer_name=args.searchanalyzername,
        use_acls=args.useacls,
        category=args.category,
    )


async def main(strategy: Strategy, credential: AsyncTokenCredential, args: Any):
    search_key = args.searchkey
    if args.keyvaultname and args.searchsecretname:
        key_vault_client = SecretClient(vault_url=f"https://{args.keyvaultname}.vault.azure.net", credential=credential)
        search_key = (await key_vault_client.get_secret(args.searchsecretname)).value
        await key_vault_client.close()

    search_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
        credential if is_key_empty(search_key) else AzureKeyCredential(search_key)
    )

    search_info = SearchInfo(
        endpoint=f"https://{args.searchservice}.search.windows.net/",
        credential=search_creds,
        index_name=args.index,
        verbose=args.verbose,
    )

    if not args.remove and not args.removeall:
        await strategy.setup(search_info)

    await strategy.run(search_info)


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
        "--visionkey",
        required=False,
        help="Required if --searchimages is specified. Use this Azure AI Vision key instead of the instead of the current user identity to login.",
    )
    parser.add_argument(
        "--keyvaultname",
        required=False,
        help="Required only if any keys must be fetched from the key vault.",
    )
    parser.add_argument(
        "--visionsecretname",
        required=False,
        help="Required if --searchimages is specified and --keyvaultname is provided. Fetch the Azure AI Vision key from this key vault instead of using the current user identity to login.",
    )
    parser.add_argument(
        "--useintvectorization",
        required=False,
        help="Required if --useintvectorization is specified. Enable Integrated vectorizer indexer support which is in preview)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    use_int_vectorization = args.useintvectorization and args.useintvectorization.lower() == "true"

    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = (
        AzureDeveloperCliCredential()
        if args.tenantid is None
        else AzureDeveloperCliCredential(tenant_id=args.tenantid, process_timeout=60)
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ingestion_strategy = None
    if use_int_vectorization:
        ingestion_strategy = loop.run_until_complete(setup_intvectorizer_strategy(azd_credential, args))
    else:
        ingestion_strategy = loop.run_until_complete(setup_file_strategy(azd_credential, args))
    loop.run_until_complete(main(ingestion_strategy, azd_credential, args))
    loop.close()
