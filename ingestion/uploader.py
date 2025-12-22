"""
High-level document ingestion orchestrator.

This module provides a simple, high-level API for ingesting documents
into Azure AI Search. It abstracts away the complexity of setting up
strategies, clients, and processors.

This module is fully self-contained and does not depend on prepdocslib.
"""

import logging
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI, AsyncOpenAI

from .config import IngestionConfig, OpenAIHost
from .storage.blob import BlobManager
from .storage.file_lister import ADLSGen2ListFileStrategy, ListFileStrategy, LocalListFileStrategy
from .embeddings.text import OpenAIEmbeddings
from .embeddings.image import ImageEmbeddings
from .search.client import SearchInfo
from .strategies.base import DocumentAction
from .strategies.file import FileStrategy
from .strategies.integrated import IntegratedVectorizerStrategy
from .strategies.cloud import CloudIngestionStrategy
from .parsers import DocumentAnalysisParser, FileProcessor, LocalHTMLParser, LocalPdfParser, TextParser
from .splitters import SentenceTextSplitter
from .figures import FigureProcessor, MediaDescriptionStrategy

logger = logging.getLogger("ingestion")


def setup_search_info(
    config: IngestionConfig,
    azure_credential: AsyncTokenCredential,
) -> SearchInfo:
    """Create SearchInfo from configuration.

    Args:
        config: Ingestion configuration
        azure_credential: Azure credential for authentication

    Returns:
        SearchInfo instance
    """
    from azure.core.credentials import AzureKeyCredential

    search_creds = (
        azure_credential if config.search_key is None else AzureKeyCredential(config.search_key)
    )

    return SearchInfo(
        endpoint=f"https://{config.search_service}.search.windows.net/",
        credential=search_creds,
        index_name=config.search_index,
        knowledgebase_name=config.knowledgebase_name,
        use_agentic_knowledgebase=config.use_agentic_knowledgebase,
        azure_openai_endpoint=f"https://{config.azure_openai_service}.openai.azure.com" if config.azure_openai_service else None,
        azure_openai_knowledgebase_model=config.azure_openai_knowledgebase_model,
        azure_openai_knowledgebase_deployment=config.azure_openai_knowledgebase_deployment,
        azure_vision_endpoint=config.vision_endpoint,
    )


def setup_openai_client(
    config: IngestionConfig,
    azure_credential: AsyncTokenCredential,
) -> tuple[AsyncOpenAI, Optional[str]]:
    """Create OpenAI client from configuration.

    Args:
        config: Ingestion configuration
        azure_credential: Azure credential for authentication

    Returns:
        Tuple of (AsyncOpenAI client, Azure OpenAI endpoint URL)
    """
    azure_openai_endpoint: Optional[str] = None

    if config.openai_host in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        if config.openai_host == OpenAIHost.AZURE_CUSTOM:
            base_url = config.azure_openai_custom_url
        else:
            azure_openai_endpoint = f"https://{config.azure_openai_service}.openai.azure.com"
            base_url = f"{azure_openai_endpoint}/openai/v1"

        if config.azure_openai_api_key:
            api_key = config.azure_openai_api_key
        else:
            api_key = get_bearer_token_provider(
                azure_credential, "https://cognitiveservices.azure.com/.default"
            )

        openai_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    elif config.openai_host == OpenAIHost.LOCAL:
        import os
        openai_client = AsyncOpenAI(
            base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8080"),
            api_key="no-key-required",
        )
    else:
        openai_client = AsyncOpenAI(
            api_key=config.openai_api_key,
            organization=config.openai_organization,
        )

    return openai_client, azure_openai_endpoint


def setup_embeddings_service(
    config: IngestionConfig,
    openai_client: AsyncOpenAI,
    azure_openai_endpoint: Optional[str],
    disable_batch: bool = False,
) -> Optional[OpenAIEmbeddings]:
    """Create embeddings service from configuration.

    Args:
        config: Ingestion configuration
        openai_client: OpenAI client
        azure_openai_endpoint: Azure OpenAI endpoint URL
        disable_batch: Whether to disable batch processing

    Returns:
        OpenAIEmbeddings instance or None if vectors disabled
    """
    if not config.use_vectors:
        return None

    return OpenAIEmbeddings(
        open_ai_client=openai_client,
        open_ai_model_name=config.azure_openai_emb_model,
        open_ai_dimensions=config.azure_openai_emb_dimensions,
        disable_batch=disable_batch,
        azure_deployment_name=config.azure_openai_emb_deployment,
        azure_endpoint=azure_openai_endpoint,
    )


def setup_image_embeddings_service(
    config: IngestionConfig,
    azure_credential: AsyncTokenCredential,
) -> Optional[ImageEmbeddings]:
    """Create image embeddings service from configuration.

    Args:
        config: Ingestion configuration
        azure_credential: Azure credential for authentication

    Returns:
        ImageEmbeddings instance or None if multimodal disabled
    """
    if not config.use_multimodal or not config.vision_endpoint:
        return None

    return ImageEmbeddings(
        endpoint=config.vision_endpoint,
        token_provider=get_bearer_token_provider(
            azure_credential, "https://cognitiveservices.azure.com/.default"
        ),
    )


def build_file_processors(
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: Optional[str] = None,
    document_intelligence_key: Optional[str] = None,
    use_local_pdf_parser: bool = False,
    use_local_html_parser: bool = False,
    process_figures: bool = False,
) -> dict[str, FileProcessor]:
    """Build file processors for different file types.

    Args:
        azure_credential: Azure credential for authentication
        document_intelligence_service: Azure Document Intelligence service name
        document_intelligence_key: Optional API key for Document Intelligence
        use_local_pdf_parser: Use local pypdf parser instead of Document Intelligence
        use_local_html_parser: Use local BeautifulSoup parser
        process_figures: Whether to extract and process figures from documents

    Returns:
        Dictionary mapping file extensions to FileProcessor instances
    """
    sentence_splitter = SentenceTextSplitter()

    # PDF parser
    if use_local_pdf_parser or not document_intelligence_service:
        pdf_parser = LocalPdfParser()
    else:
        endpoint = f"https://{document_intelligence_service}.cognitiveservices.azure.com/"
        cred = azure_credential if not document_intelligence_key else AzureKeyCredential(document_intelligence_key)
        pdf_parser = DocumentAnalysisParser(
            endpoint=endpoint,
            credential=cred,
            process_figures=process_figures,
        )

    # HTML parser
    if use_local_html_parser:
        html_parser = LocalHTMLParser()
    else:
        html_parser = LocalHTMLParser()  # Default to local for HTML

    # Text parser for plain text and markdown
    text_parser = TextParser()

    return {
        ".pdf": FileProcessor(parser=pdf_parser, splitter=sentence_splitter),
        ".html": FileProcessor(parser=html_parser, splitter=sentence_splitter),
        ".htm": FileProcessor(parser=html_parser, splitter=sentence_splitter),
        ".txt": FileProcessor(parser=text_parser, splitter=sentence_splitter),
        ".md": FileProcessor(parser=text_parser, splitter=sentence_splitter),
        ".json": FileProcessor(parser=text_parser, splitter=sentence_splitter),
        ".csv": FileProcessor(parser=text_parser, splitter=sentence_splitter),
    }


def setup_figure_processor(
    credential: AsyncTokenCredential,
    use_multimodal: bool = False,
    use_content_understanding: bool = False,
    content_understanding_endpoint: Optional[str] = None,
    openai_client: Optional[AsyncOpenAI] = None,
    openai_model: Optional[str] = None,
    openai_deployment: Optional[str] = None,
) -> Optional[FigureProcessor]:
    """Set up figure processor for image description.

    Args:
        credential: Azure credential for authentication
        use_multimodal: Whether to enable multimodal processing
        use_content_understanding: Use Azure Content Understanding for descriptions
        content_understanding_endpoint: Content Understanding endpoint URL
        openai_client: OpenAI client for GPT-4 Vision descriptions
        openai_model: OpenAI model name
        openai_deployment: Azure OpenAI deployment name

    Returns:
        FigureProcessor instance or None if multimodal is disabled
    """
    if not use_multimodal:
        return None

    if use_content_understanding and content_understanding_endpoint:
        return FigureProcessor(
            credential=credential,
            strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
            content_understanding_endpoint=content_understanding_endpoint,
        )
    elif openai_client and openai_model:
        return FigureProcessor(
            credential=credential,
            strategy=MediaDescriptionStrategy.OPENAI,
            openai_client=openai_client,
            openai_model=openai_model,
            openai_deployment=openai_deployment,
        )
    else:
        return FigureProcessor(
            credential=credential,
            strategy=MediaDescriptionStrategy.NONE,
        )


def setup_blob_manager(config: IngestionConfig, azure_credential: AsyncTokenCredential) -> BlobManager:
    """Create blob manager from configuration.

    Args:
        config: Ingestion configuration
        azure_credential: Azure credential for authentication

    Returns:
        BlobManager instance
    """
    return BlobManager(
        endpoint=f"https://{config.storage_account}.blob.core.windows.net",
        container=config.storage_container,
        credential=azure_credential,
        account=config.storage_account,
        resource_group=config.storage_resource_group,
        subscription_id=config.subscription_id,
        image_container=config.image_storage_container,
    )


def setup_list_file_strategy(
    config: IngestionConfig,
    azure_credential: AsyncTokenCredential,
    local_files: Optional[str] = None,
) -> ListFileStrategy:
    """Create file listing strategy from configuration.

    Args:
        config: Ingestion configuration
        azure_credential: Azure credential for authentication
        local_files: Optional local file path pattern

    Returns:
        ListFileStrategy instance

    Raises:
        ValueError: If neither local files nor data lake is configured
    """
    if config.datalake_storage_account:
        if config.datalake_filesystem is None or config.datalake_path is None:
            raise ValueError("DataLake file system and path are required when using Azure Data Lake Gen2")
        creds = azure_credential if config.datalake_key is None else config.datalake_key
        return ADLSGen2ListFileStrategy(
            data_lake_storage_account=config.datalake_storage_account,
            data_lake_filesystem=config.datalake_filesystem,
            data_lake_path=config.datalake_path,
            credential=creds,
            enable_global_documents=config.enable_global_documents,
        )
    elif local_files:
        return LocalListFileStrategy(
            path_pattern=local_files,
            enable_global_documents=config.enable_global_documents,
        )
    else:
        raise ValueError("Either local_files or datalake_storage_account must be provided.")


async def upload_and_index(
    files: Optional[str] = None,
    config: Optional[IngestionConfig] = None,
    credential: Optional[AsyncTokenCredential] = None,
    action: DocumentAction = DocumentAction.Add,
    category: Optional[str] = None,
    setup_index: bool = True,
) -> dict:
    """
    High-level function to upload and index documents into Azure AI Search.

    This is the main entry point for the ingestion module. It handles all the
    complexity of setting up clients, strategies, and processors.

    Args:
        files: Path pattern for local files to ingest (e.g., "data/*")
        config: Ingestion configuration (defaults to IngestionConfig.from_env())
        credential: Azure credential (defaults to AzureDeveloperCliCredential)
        action: Document action (Add, Remove, RemoveAll)
        category: Optional category for all ingested documents
        setup_index: Whether to create/update the search index

    Returns:
        Dictionary with ingestion results

    Example:
        ```python
        from ingestion import upload_and_index, IngestionConfig

        config = IngestionConfig.from_env()
        result = await upload_and_index(files="data/*", config=config)
        ```
    """
    # Use defaults if not provided
    if config is None:
        config = IngestionConfig.from_env()

    # Validate configuration
    errors = config.validate()
    if errors:
        return {"success": False, "errors": errors}

    # Set up credential
    if credential is None:
        if config.tenant_id:
            credential = AzureDeveloperCliCredential(tenant_id=config.tenant_id, process_timeout=60)
        else:
            credential = AzureDeveloperCliCredential(process_timeout=60)

    try:
        # Set up services
        search_info = setup_search_info(config, credential)
        blob_manager = setup_blob_manager(config, credential)
        openai_client, azure_openai_endpoint = setup_openai_client(config, credential)
        embeddings_service = setup_embeddings_service(config, openai_client, azure_openai_endpoint)
        image_embeddings_service = setup_image_embeddings_service(config, credential)
        list_file_strategy = setup_list_file_strategy(config, credential, files)

        # Set up file processors using internal module
        file_processors = build_file_processors(
            azure_credential=credential,
            document_intelligence_service=config.document_intelligence_service,
            document_intelligence_key=config.document_intelligence_key,
            use_local_pdf_parser=config.use_local_pdf_parser,
            use_local_html_parser=config.use_local_html_parser,
            process_figures=config.use_multimodal,
        )

        figure_processor = setup_figure_processor(
            credential=credential,
            use_multimodal=config.use_multimodal,
            use_content_understanding=config.use_content_understanding,
            content_understanding_endpoint=config.content_understanding_endpoint,
            openai_client=openai_client,
            openai_model=config.azure_openai_chatgpt_model,
            openai_deployment=config.azure_openai_chatgpt_deployment,
        )

        # Choose strategy based on configuration
        if config.use_cloud_ingestion:
            if not all([
                config.document_extractor_uri,
                config.figure_processor_uri,
                config.text_processor_uri,
                config.search_user_assigned_identity_resource_id,
            ]):
                return {"success": False, "errors": ["Cloud ingestion requires all skill endpoints to be configured"]}

            strategy = CloudIngestionStrategy(
                list_file_strategy=list_file_strategy,
                blob_manager=blob_manager,
                search_info=search_info,
                embeddings=embeddings_service,
                search_field_name_embedding=config.search_field_name_embedding,
                document_extractor_uri=config.document_extractor_uri,
                document_extractor_auth_resource_id=config.document_extractor_resource_id,
                figure_processor_uri=config.figure_processor_uri,
                figure_processor_auth_resource_id=config.figure_processor_resource_id,
                text_processor_uri=config.text_processor_uri,
                text_processor_auth_resource_id=config.text_processor_resource_id,
                subscription_id=config.subscription_id or "",
                document_action=action,
                search_analyzer_name=config.search_analyzer_name,
                use_acls=config.use_acls,
                use_multimodal=config.use_multimodal,
                enforce_access_control=config.enforce_access_control,
                use_web_source=config.use_web_source,
                search_user_assigned_identity_resource_id=config.search_user_assigned_identity_resource_id,
            )
        elif config.use_integrated_vectorization:
            if not embeddings_service:
                return {"success": False, "errors": ["Integrated vectorization requires embeddings service"]}

            strategy = IntegratedVectorizerStrategy(
                list_file_strategy=list_file_strategy,
                blob_manager=blob_manager,
                search_info=search_info,
                embeddings=embeddings_service,
                search_field_name_embedding=config.search_field_name_embedding,
                subscription_id=config.subscription_id or "",
                document_action=action,
                search_analyzer_name=config.search_analyzer_name,
                use_acls=config.use_acls,
                category=category,
                enforce_access_control=config.enforce_access_control,
                use_web_source=config.use_web_source,
            )
        else:
            strategy = FileStrategy(
                list_file_strategy=list_file_strategy,
                blob_manager=blob_manager,
                search_info=search_info,
                file_processors=file_processors,
                document_action=action,
                embeddings=embeddings_service,
                image_embeddings=image_embeddings_service,
                search_analyzer_name=config.search_analyzer_name,
                search_field_name_embedding=config.search_field_name_embedding,
                use_acls=config.use_acls,
                category=category,
                figure_processor=figure_processor,
                enforce_access_control=config.enforce_access_control,
                use_web_source=config.use_web_source,
                use_sharepoint_source=config.use_sharepoint_source,
            )

        # Execute the strategy
        if setup_index:
            await strategy.setup()
        await strategy.run()

        return {"success": True, "strategy": type(strategy).__name__}

    except Exception as e:
        logger.exception("Error during ingestion: %s", e)
        return {"success": False, "errors": [str(e)]}

    finally:
        # Clean up
        try:
            await blob_manager.close_clients()
            await openai_client.close()
            await credential.close()
        except Exception as e:
            logger.debug("Error closing clients: %s", e)
