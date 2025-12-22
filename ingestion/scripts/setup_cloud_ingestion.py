#!/usr/bin/env python3
"""
Set up cloud ingestion by creating the search index, skillset, and indexer.

This script is called after provisioning to configure the Azure AI Search
indexer pipeline that uses the deployed Azure Functions as custom skills.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the ingestion module to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from azure.identity.aio import AzureDeveloperCliCredential

from ingestion import (
    CloudIngestionStrategy,
    IngestionConfig,
    OpenAIEmbeddings,
    SearchInfo,
)
from ingestion.storage import BlobManager, LocalListFileStrategy


async def main():
    """Set up cloud ingestion pipeline."""
    
    # Load configuration from environment
    config = IngestionConfig.from_env()
    
    # Validate required cloud ingestion settings
    document_extractor_uri = os.environ.get("AZURE_FUNCTION_DOCUMENT_EXTRACTOR_URI")
    figure_processor_uri = os.environ.get("AZURE_FUNCTION_FIGURE_PROCESSOR_URI")
    text_processor_uri = os.environ.get("AZURE_FUNCTION_TEXT_PROCESSOR_URI")
    user_assigned_identity_id = os.environ.get("AZURE_USER_ASSIGNED_IDENTITY_ID")
    
    if not all([document_extractor_uri, figure_processor_uri, text_processor_uri, user_assigned_identity_id]):
        print("Cloud ingestion environment variables not set. Skipping cloud ingestion setup.")
        print("Required variables:")
        print("  - AZURE_FUNCTION_DOCUMENT_EXTRACTOR_URI")
        print("  - AZURE_FUNCTION_FIGURE_PROCESSOR_URI")
        print("  - AZURE_FUNCTION_TEXT_PROCESSOR_URI")
        print("  - AZURE_USER_ASSIGNED_IDENTITY_ID")
        return
    
    print("Setting up cloud ingestion pipeline...")
    
    # Create credential
    credential = AzureDeveloperCliCredential(tenant_id=config.tenant_id)
    
    # Create search info
    search_info = SearchInfo(
        endpoint=f"https://{config.search_service}.search.windows.net/",
        credential=credential,
        index_name=config.search_index,
    )
    
    # Create blob manager
    blob_manager = BlobManager(
        endpoint=f"https://{config.storage_account}.blob.core.windows.net",
        container=config.storage_container,
        credential=credential,
        account=config.storage_account,
        resource_group=config.storage_resource_group,
        subscription_id=config.subscription_id,
    )
    
    # Create embeddings service (for index schema)
    from azure.identity.aio import get_bearer_token_provider
    from openai import AsyncAzureOpenAI
    
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    openai_client = AsyncAzureOpenAI(
        api_version="2024-06-01",
        azure_endpoint=f"https://{config.azure_openai_service}.openai.azure.com",
        azure_ad_token_provider=token_provider,
    )
    
    embeddings = OpenAIEmbeddings(
        open_ai_client=openai_client,
        open_ai_model_name=config.azure_openai_emb_model_name or "text-embedding-3-large",
        open_ai_dimensions=config.azure_openai_emb_dimensions or 3072,
        azure_deployment_name=config.azure_openai_emb_deployment,
        azure_endpoint=f"https://{config.azure_openai_service}.openai.azure.com",
    )
    
    # Create file list strategy (for uploading initial documents)
    data_path = Path(__file__).parent.parent / "data"
    if data_path.exists():
        list_file_strategy = LocalListFileStrategy(path_pattern=str(data_path / "*"))
    else:
        list_file_strategy = LocalListFileStrategy(path_pattern="")
    
    # Create cloud ingestion strategy
    strategy = CloudIngestionStrategy(
        list_file_strategy=list_file_strategy,
        blob_manager=blob_manager,
        search_info=search_info,
        embeddings=embeddings,
        search_field_name_embedding=config.search_field_name_embedding or "embedding",
        document_extractor_uri=document_extractor_uri,
        document_extractor_auth_resource_id=user_assigned_identity_id,
        figure_processor_uri=figure_processor_uri,
        figure_processor_auth_resource_id=user_assigned_identity_id,
        text_processor_uri=text_processor_uri,
        text_processor_auth_resource_id=user_assigned_identity_id,
        subscription_id=config.subscription_id,
        search_user_assigned_identity_resource_id=user_assigned_identity_id,
        use_multimodal=config.use_multimodal,
    )
    
    # Set up the index, skillset, and indexer
    print("Creating search index...")
    await strategy.setup()
    
    # Run the indexer if there are documents
    if data_path.exists() and any(data_path.iterdir()):
        print("Uploading documents and running indexer...")
        await strategy.run()
    else:
        print("No documents found in data/ directory. Skipping initial indexing.")
    
    await credential.close()
    print("Cloud ingestion setup complete!")


if __name__ == "__main__":
    asyncio.run(main())
