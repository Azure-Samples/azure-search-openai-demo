"""
Ingestion configuration module.

Provides a centralized configuration class for document ingestion that supports:
- Environment variable-based configuration
- Optional overrides via function arguments
- Validation of required settings
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("ingestion")


class OpenAIHost(str, Enum):
    """Supported OpenAI hosting styles.

    OPENAI:       Public OpenAI API.
    AZURE:        Standard Azure OpenAI (service name becomes endpoint).
    AZURE_CUSTOM: A fully custom endpoint URL (for Network Isolation / APIM).
    LOCAL:        A locally hosted OpenAI-compatible endpoint (no key required).
    """

    OPENAI = "openai"
    AZURE = "azure"
    AZURE_CUSTOM = "azure_custom"
    LOCAL = "local"


@dataclass
class IngestionConfig:
    """Configuration for document ingestion into Azure AI Search.

    This class encapsulates all settings needed for the ingestion pipeline,
    including Azure service endpoints, authentication, and feature flags.

    Attributes:
        search_service: Azure AI Search service name
        search_index: Name of the search index
        storage_account: Azure Storage account name
        storage_container: Blob container for documents
        storage_resource_group: Resource group for storage account
        subscription_id: Azure subscription ID
        openai_host: OpenAI hosting style (azure, openai, local, azure_custom)
        azure_openai_service: Azure OpenAI service name
        azure_openai_emb_deployment: Embedding model deployment name
        azure_openai_emb_model: Embedding model name
        azure_openai_emb_dimensions: Embedding dimensions
        document_intelligence_service: Azure Document Intelligence service name
        vision_endpoint: Azure AI Vision endpoint for image embeddings
        use_vectors: Whether to generate text embeddings
        use_multimodal: Whether to process images/figures
        use_acls: Whether to use access control lists
        enforce_access_control: Whether to enforce ACL-based filtering
        use_integrated_vectorization: Use Azure AI Search integrated vectorization
        use_cloud_ingestion: Use cloud-based ingestion with Azure Functions
        search_analyzer_name: Custom analyzer for search index
        search_field_name_embedding: Field name for embeddings in index
        tenant_id: Azure AD tenant ID
    """

    # Required Azure services
    search_service: str
    search_index: str
    storage_account: str
    storage_container: str

    # Optional Azure services
    storage_resource_group: Optional[str] = None
    subscription_id: Optional[str] = None
    image_storage_container: Optional[str] = None

    # OpenAI configuration
    openai_host: OpenAIHost = OpenAIHost.AZURE
    azure_openai_service: Optional[str] = None
    azure_openai_custom_url: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_emb_deployment: Optional[str] = None
    azure_openai_emb_model: str = "text-embedding-ada-002"
    azure_openai_emb_dimensions: int = 1536
    openai_api_key: Optional[str] = None
    openai_organization: Optional[str] = None

    # Document Intelligence
    document_intelligence_service: Optional[str] = None
    document_intelligence_key: Optional[str] = None

    # Vision / Multimodal
    vision_endpoint: Optional[str] = None
    content_understanding_endpoint: Optional[str] = None

    # Feature flags
    use_vectors: bool = True
    use_multimodal: bool = False
    use_acls: bool = False
    enforce_access_control: bool = False
    use_integrated_vectorization: bool = False
    use_cloud_ingestion: bool = False
    use_local_pdf_parser: bool = False
    use_local_html_parser: bool = False
    use_content_understanding: bool = False
    enable_global_documents: bool = False
    use_agentic_knowledgebase: bool = False
    use_web_source: bool = False
    use_sharepoint_source: bool = False

    # Search configuration
    search_analyzer_name: Optional[str] = None
    search_field_name_embedding: str = "embedding"
    search_key: Optional[str] = None

    # Azure AD
    tenant_id: Optional[str] = None

    # Agentic knowledgebase
    knowledgebase_name: Optional[str] = None
    azure_openai_knowledgebase_deployment: Optional[str] = None
    azure_openai_knowledgebase_model: Optional[str] = None

    # Chat model (for figure descriptions)
    azure_openai_chatgpt_deployment: Optional[str] = None
    azure_openai_chatgpt_model: Optional[str] = None

    # Data Lake (for ADLS Gen2 sources)
    datalake_storage_account: Optional[str] = None
    datalake_filesystem: Optional[str] = None
    datalake_path: Optional[str] = None
    datalake_key: Optional[str] = None

    # Cloud ingestion endpoints
    document_extractor_uri: Optional[str] = None
    document_extractor_resource_id: Optional[str] = None
    figure_processor_uri: Optional[str] = None
    figure_processor_resource_id: Optional[str] = None
    text_processor_uri: Optional[str] = None
    text_processor_resource_id: Optional[str] = None
    search_user_assigned_identity_resource_id: Optional[str] = None

    @classmethod
    def from_env(cls, **overrides) -> "IngestionConfig":
        """Create configuration from environment variables with optional overrides.

        Args:
            **overrides: Keyword arguments to override environment-based values

        Returns:
            IngestionConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """

        def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
            """Get environment variable, applying override if present."""
            override_key = key.lower()
            if override_key in overrides:
                return overrides[override_key]
            return os.getenv(key, default)

        def get_bool(key: str, default: bool = False) -> bool:
            """Get boolean environment variable."""
            override_key = key.lower()
            if override_key in overrides:
                val = overrides[override_key]
                return val if isinstance(val, bool) else str(val).lower() == "true"
            return os.getenv(key, "").lower() == "true" if not default else os.getenv(key, "").lower() != "false"

        def get_int(key: str, default: int) -> int:
            """Get integer environment variable."""
            override_key = key.lower()
            if override_key in overrides:
                return int(overrides[override_key])
            val = os.getenv(key)
            return int(val) if val else default

        # Determine OpenAI host
        openai_host_str = get_env("OPENAI_HOST", "azure")
        try:
            openai_host = OpenAIHost(openai_host_str)
        except ValueError:
            openai_host = OpenAIHost.AZURE

        return cls(
            # Required
            search_service=get_env("AZURE_SEARCH_SERVICE", ""),
            search_index=get_env("AZURE_SEARCH_INDEX", ""),
            storage_account=get_env("AZURE_STORAGE_ACCOUNT", ""),
            storage_container=get_env("AZURE_STORAGE_CONTAINER", ""),
            # Optional Azure services
            storage_resource_group=get_env("AZURE_STORAGE_RESOURCE_GROUP"),
            subscription_id=get_env("AZURE_SUBSCRIPTION_ID"),
            image_storage_container=get_env("AZURE_IMAGESTORAGE_CONTAINER"),
            # OpenAI
            openai_host=openai_host,
            azure_openai_service=get_env("AZURE_OPENAI_SERVICE"),
            azure_openai_custom_url=get_env("AZURE_OPENAI_CUSTOM_URL"),
            azure_openai_api_key=get_env("AZURE_OPENAI_API_KEY_OVERRIDE"),
            azure_openai_emb_deployment=get_env("AZURE_OPENAI_EMB_DEPLOYMENT"),
            azure_openai_emb_model=get_env("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002"),
            azure_openai_emb_dimensions=get_int("AZURE_OPENAI_EMB_DIMENSIONS", 1536),
            openai_api_key=get_env("OPENAI_API_KEY"),
            openai_organization=get_env("OPENAI_ORGANIZATION"),
            # Document Intelligence
            document_intelligence_service=get_env("AZURE_DOCUMENTINTELLIGENCE_SERVICE"),
            document_intelligence_key=get_env("AZURE_DOCUMENTINTELLIGENCE_KEY"),
            # Vision
            vision_endpoint=get_env("AZURE_VISION_ENDPOINT"),
            content_understanding_endpoint=get_env("AZURE_CONTENTUNDERSTANDING_ENDPOINT"),
            # Feature flags
            use_vectors=not get_bool("USE_VECTORS", True) is False,
            use_multimodal=get_bool("USE_MULTIMODAL"),
            use_acls=get_bool("AZURE_USE_AUTHENTICATION"),
            enforce_access_control=get_bool("AZURE_ENFORCE_ACCESS_CONTROL"),
            use_integrated_vectorization=get_bool("USE_FEATURE_INT_VECTORIZATION"),
            use_cloud_ingestion=get_bool("USE_CLOUD_INGESTION"),
            use_local_pdf_parser=get_bool("USE_LOCAL_PDF_PARSER"),
            use_local_html_parser=get_bool("USE_LOCAL_HTML_PARSER"),
            use_content_understanding=get_bool("USE_MEDIA_DESCRIBER_AZURE_CU"),
            enable_global_documents=get_bool("AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS"),
            use_agentic_knowledgebase=get_bool("USE_AGENTIC_KNOWLEDGEBASE"),
            use_web_source=get_bool("USE_WEB_SOURCE"),
            use_sharepoint_source=get_bool("USE_SHAREPOINT_SOURCE"),
            # Search
            search_analyzer_name=get_env("AZURE_SEARCH_ANALYZER_NAME"),
            search_field_name_embedding=get_env("AZURE_SEARCH_FIELD_NAME_EMBEDDING", "embedding"),
            search_key=get_env("AZURE_SEARCH_KEY"),
            # Azure AD
            tenant_id=get_env("AZURE_TENANT_ID"),
            # Agentic knowledgebase
            knowledgebase_name=get_env("AZURE_SEARCH_KNOWLEDGEBASE_NAME"),
            azure_openai_knowledgebase_deployment=get_env("AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT"),
            azure_openai_knowledgebase_model=get_env("AZURE_OPENAI_KNOWLEDGEBASE_MODEL"),
            # Chat model
            azure_openai_chatgpt_deployment=get_env("AZURE_OPENAI_CHATGPT_DEPLOYMENT"),
            azure_openai_chatgpt_model=get_env("AZURE_OPENAI_CHATGPT_MODEL"),
            # Data Lake
            datalake_storage_account=get_env("AZURE_ADLS_GEN2_STORAGE_ACCOUNT"),
            datalake_filesystem=get_env("AZURE_ADLS_GEN2_FILESYSTEM"),
            datalake_path=get_env("AZURE_ADLS_GEN2_FILESYSTEM_PATH"),
            datalake_key=get_env("AZURE_ADLS_GEN2_KEY"),
            # Cloud ingestion
            document_extractor_uri=get_env("DOCUMENT_EXTRACTOR_SKILL_ENDPOINT"),
            document_extractor_resource_id=get_env("DOCUMENT_EXTRACTOR_SKILL_AUTH_RESOURCE_ID"),
            figure_processor_uri=get_env("FIGURE_PROCESSOR_SKILL_ENDPOINT"),
            figure_processor_resource_id=get_env("FIGURE_PROCESSOR_SKILL_AUTH_RESOURCE_ID"),
            text_processor_uri=get_env("TEXT_PROCESSOR_SKILL_ENDPOINT"),
            text_processor_resource_id=get_env("TEXT_PROCESSOR_SKILL_AUTH_RESOURCE_ID"),
            search_user_assigned_identity_resource_id=get_env("AZURE_SEARCH_USER_ASSIGNED_IDENTITY_RESOURCE_ID"),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.search_service:
            errors.append("search_service (AZURE_SEARCH_SERVICE) is required")
        if not self.search_index:
            errors.append("search_index (AZURE_SEARCH_INDEX) is required")
        if not self.storage_account:
            errors.append("storage_account (AZURE_STORAGE_ACCOUNT) is required")
        if not self.storage_container:
            errors.append("storage_container (AZURE_STORAGE_CONTAINER) is required")

        if self.openai_host in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
            if self.openai_host == OpenAIHost.AZURE and not self.azure_openai_service:
                errors.append("azure_openai_service (AZURE_OPENAI_SERVICE) is required for Azure OpenAI")
            if self.openai_host == OpenAIHost.AZURE_CUSTOM and not self.azure_openai_custom_url:
                errors.append("azure_openai_custom_url (AZURE_OPENAI_CUSTOM_URL) is required for Azure OpenAI custom")

        if self.use_vectors and self.openai_host in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
            if not self.azure_openai_emb_deployment:
                errors.append("azure_openai_emb_deployment (AZURE_OPENAI_EMB_DEPLOYMENT) is required for embeddings")

        if self.use_multimodal and not self.vision_endpoint:
            errors.append("vision_endpoint (AZURE_VISION_ENDPOINT) is required for multimodal features")

        if self.use_agentic_knowledgebase:
            if self.openai_host not in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
                errors.append("Agentic knowledgebase requires Azure OpenAI")
            if not self.azure_openai_knowledgebase_deployment:
                errors.append("azure_openai_knowledgebase_deployment is required for agentic knowledgebase")

        if self.use_cloud_ingestion:
            if not self.document_extractor_uri:
                errors.append("document_extractor_uri is required for cloud ingestion")
            if not self.text_processor_uri:
                errors.append("text_processor_uri is required for cloud ingestion")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


def clean_key_if_exists(key: Optional[str]) -> Optional[str]:
    """Remove leading and trailing whitespace from a key if it exists.

    Args:
        key: The key string to clean

    Returns:
        Cleaned key or None if key is empty/None
    """
    if key is not None and key.strip() != "":
        return key.strip()
    return None
