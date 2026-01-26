"""Script to setup cloud ingestion for Azure AI Search."""

import asyncio
import logging
import os

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from openai import AsyncOpenAI
from rich.logging import RichHandler

from load_azd_env import load_azd_env
from prepdocslib.blobmanager import BlobManager
from prepdocslib.cloudingestionstrategy import CloudIngestionStrategy
from prepdocslib.listfilestrategy import LocalListFileStrategy
from prepdocslib.servicesetup import (
    OpenAIHost,
    clean_key_if_exists,
    setup_blob_manager,
    setup_embeddings_service,
    setup_openai_client,
    setup_search_info,
)
from prepdocslib.strategy import DocumentAction

logger = logging.getLogger("scripts")


async def setup_cloud_ingestion_strategy(
    azure_credential: AsyncTokenCredential,
    document_action: DocumentAction = DocumentAction.Add,
) -> tuple[CloudIngestionStrategy, AsyncOpenAI, AsyncTokenCredential, BlobManager]:
    """Setup the cloud ingestion strategy with all required services."""

    # Get environment variables
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    index_name = os.environ["AZURE_SEARCH_INDEX"]
    search_user_assigned_identity_resource_id = os.environ["AZURE_SEARCH_USER_ASSIGNED_IDENTITY_RESOURCE_ID"]
    storage_container = os.environ["AZURE_STORAGE_CONTAINER"]
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    image_storage_container = os.environ.get("AZURE_IMAGESTORAGE_CONTAINER")
    search_embedding_field = os.environ["AZURE_SEARCH_FIELD_NAME_EMBEDDING"]

    # Cloud ingestion storage account (ADLS Gen2 when ACLs enabled, standard blob otherwise)
    # Fallback to AZURE_STORAGE_ACCOUNT is for legacy deployments only - may be removed in future
    storage_account = os.getenv("AZURE_CLOUD_INGESTION_STORAGE_ACCOUNT") or os.environ["AZURE_STORAGE_ACCOUNT"]
    storage_resource_group = (
        os.getenv("AZURE_CLOUD_INGESTION_STORAGE_RESOURCE_GROUP") or os.environ["AZURE_STORAGE_RESOURCE_GROUP"]
    )

    # Cloud ingestion specific endpoints
    document_extractor_uri = os.environ["DOCUMENT_EXTRACTOR_SKILL_ENDPOINT"]
    document_extractor_resource_id = os.environ["DOCUMENT_EXTRACTOR_SKILL_AUTH_RESOURCE_ID"]
    figure_processor_uri = os.environ["FIGURE_PROCESSOR_SKILL_ENDPOINT"]
    figure_processor_resource_id = os.environ["FIGURE_PROCESSOR_SKILL_AUTH_RESOURCE_ID"]
    text_processor_uri = os.environ["TEXT_PROCESSOR_SKILL_ENDPOINT"]
    text_processor_resource_id = os.environ["TEXT_PROCESSOR_SKILL_AUTH_RESOURCE_ID"]

    # Feature flags
    use_multimodal = os.getenv("USE_MULTIMODAL", "").lower() == "true"
    use_acls = os.getenv("USE_CLOUD_INGESTION_ACLS", "").lower() == "true"
    enforce_access_control = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    use_web_source = os.getenv("USE_WEB_SOURCE", "").lower() == "true"

    # Warn if access control is enforced but ACL extraction is not enabled
    if enforce_access_control and not use_acls:
        logger.warning(
            "AZURE_ENFORCE_ACCESS_CONTROL is enabled but USE_CLOUD_INGESTION_ACLS is not. "
            "Documents will be indexed without ACLs, so access control filtering will not work. "
            "Either set USE_CLOUD_INGESTION_ACLS=true to extract ACLs from ADLS Gen2, "
            "or manually set ACLs using scripts/manageacl.py after ingestion."
        )

    # Setup search info
    search_info = setup_search_info(
        search_service=search_service,
        index_name=index_name,
        azure_credential=azure_credential,
        azure_vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
    )

    # Setup blob manager
    blob_manager = setup_blob_manager(
        azure_credential=azure_credential,
        storage_account=storage_account,
        storage_container=storage_container,
        storage_resource_group=storage_resource_group,
        subscription_id=subscription_id,
        storage_key=None,
        image_storage_container=image_storage_container,
    )

    # Setup OpenAI embeddings
    OPENAI_HOST = OpenAIHost(os.environ["OPENAI_HOST"])
    openai_client, azure_openai_endpoint = setup_openai_client(
        openai_host=OPENAI_HOST,
        azure_credential=azure_credential,
        azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
        openai_api_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
        openai_organization=os.getenv("OPENAI_ORGANIZATION"),
    )

    emb_model_dimensions = 1536
    if os.getenv("AZURE_OPENAI_EMB_DIMENSIONS"):
        emb_model_dimensions = int(os.environ["AZURE_OPENAI_EMB_DIMENSIONS"])

    openai_embeddings_service = setup_embeddings_service(
        OPENAI_HOST,
        openai_client,
        emb_model_name=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
        emb_model_dimensions=emb_model_dimensions,
        azure_openai_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
        azure_openai_endpoint=azure_openai_endpoint,
        disable_batch=False,
    )

    # Create a list file strategy for uploading files from the data folder
    list_file_strategy = LocalListFileStrategy(path_pattern="data/*", enable_global_documents=False)

    # Create the cloud ingestion strategy
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
        subscription_id=subscription_id,
        document_action=document_action,
        search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
        use_acls=use_acls,
        use_multimodal=use_multimodal,
        enforce_access_control=enforce_access_control,
        use_web_source=use_web_source,
        search_user_assigned_identity_resource_id=search_user_assigned_identity_resource_id,
    )

    return ingestion_strategy, openai_client, azure_credential, blob_manager


async def main():
    """Main function to setup cloud ingestion."""
    load_azd_env()

    # Check if cloud ingestion is enabled
    use_cloud_ingestion = os.getenv("USE_CLOUD_INGESTION", "").lower() == "true"
    if not use_cloud_ingestion:
        logger.info("Cloud ingestion is not enabled. Skipping setup.")
        return

    # Setup logging
    logging.basicConfig(format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
    logger.setLevel(logging.INFO)

    logger.info("Setting up cloud ingestion...")

    # Use the current user identity to connect to Azure services
    if tenant_id := os.getenv("AZURE_TENANT_ID"):
        logger.info("Connecting to Azure services using the azd credential for tenant %s", tenant_id)
        azd_credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        logger.info("Connecting to Azure services using the azd credential for home tenant")
        azd_credential = AzureDeveloperCliCredential(process_timeout=60)

    try:
        ingestion_strategy, openai_client, credential, blob_manager = await setup_cloud_ingestion_strategy(
            azure_credential=azd_credential,
            document_action=DocumentAction.Add,
        )

        # Setup the indexer, skillset, and data source
        logger.info("Setting up indexer, skillset, and data source...")
        await ingestion_strategy.setup()
        logger.info("Triggering initial indexing run...")
        await ingestion_strategy.run()

    finally:
        await blob_manager.close_clients()
        await openai_client.close()
        await azd_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
