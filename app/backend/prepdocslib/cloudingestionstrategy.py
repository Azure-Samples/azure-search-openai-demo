"""Cloud ingestion strategy using Azure AI Search custom skills."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from azure.search.documents.indexes._generated.models import (
    NativeBlobSoftDeleteDeletionDetectionPolicy,
)
from azure.search.documents.indexes.models import (
    IndexProjectionMode,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataSourceType,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    WebApiSkill,
)

from .blobmanager import BlobManager
from .embeddings import AzureOpenAIEmbeddingService
from .listfilestrategy import ListFileStrategy
from .searchmanager import SearchManager
from .strategy import DocumentAction, SearchInfo, Strategy

logger = logging.getLogger("scripts")

_DEFAULT_TIMEOUT = timedelta(seconds=230)
_DEFAULT_BATCH_SIZE = 1


@dataclass(slots=True)
class _SkillConfig:
    """Configuration for a custom Web API skill."""

    name: str
    description: str
    uri: str
    auth_resource_id: str


class CloudIngestionStrategy(Strategy):
    """Ingestion strategy that wires Azure Function custom skills into an indexer."""

    def __init__(
        self,
        *,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        embeddings: AzureOpenAIEmbeddingService,
        search_field_name_embedding: str,
        document_extractor_uri: str,
        document_extractor_auth_resource_id: str,
        figure_processor_uri: str,
        figure_processor_auth_resource_id: str,
        text_processor_uri: str,
        text_processor_auth_resource_id: str,
        subscription_id: str,
        document_action: DocumentAction = DocumentAction.Add,
        search_analyzer_name: str | None = None,
        use_acls: bool = False,
        use_multimodal: bool = False,
        enforce_access_control: bool = False,
    ) -> None:
        if not search_field_name_embedding:
            raise ValueError("search_field_name_embedding must be provided for cloud ingestion")
        if not document_extractor_uri:
            raise ValueError("document_extractor_uri must be provided for cloud ingestion")
        if not document_extractor_auth_resource_id:
            raise ValueError("document_extractor_auth_resource_id must be provided for cloud ingestion")
        if not figure_processor_uri:
            raise ValueError("figure_processor_uri must be provided for cloud ingestion")
        if not figure_processor_auth_resource_id:
            raise ValueError("figure_processor_auth_resource_id must be provided for cloud ingestion")
        if not text_processor_uri:
            raise ValueError("text_processor_uri must be provided for cloud ingestion")
        if not text_processor_auth_resource_id:
            raise ValueError("text_processor_auth_resource_id must be provided for cloud ingestion")

        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.document_action = document_action
        self.embeddings = embeddings
        self.search_field_name_embedding = search_field_name_embedding
        self.search_info = search_info
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.use_multimodal = use_multimodal
        self.enforce_access_control = enforce_access_control
        self.subscription_id = subscription_id

        prefix = f"{self.search_info.index_name}-cloud"
        self.skillset_name = f"{prefix}-skillset"
        self.indexer_name = f"{prefix}-indexer"
        self.data_source_name = f"{prefix}-blob"

        self.document_extractor = _SkillConfig(
            name=f"{prefix}-document-extractor-skill",
            description="Custom skill that downloads and parses source documents",
            uri=document_extractor_uri,
            auth_resource_id=document_extractor_auth_resource_id,
        )
        self.figure_processor = _SkillConfig(
            name=f"{prefix}-figure-processor-skill",
            description="Custom skill that enriches individual figures",
            uri=figure_processor_uri,
            auth_resource_id=figure_processor_auth_resource_id,
        )
        self.text_processor = _SkillConfig(
            name=f"{prefix}-text-processor-skill",
            description="Custom skill that merges figures, chunks text, and generates embeddings",
            uri=text_processor_uri,
            auth_resource_id=text_processor_auth_resource_id,
        )

        self._search_manager: SearchManager | None = None

    def _build_search_manager(self) -> SearchManager:
        if not isinstance(self.embeddings, AzureOpenAIEmbeddingService):
            raise TypeError("Cloud ingestion requires AzureOpenAIEmbeddingService for search index setup")

        return SearchManager(
            search_info=self.search_info,
            search_analyzer_name=self.search_analyzer_name,
            use_acls=self.use_acls,
            use_int_vectorization=True,
            embeddings=self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.use_multimodal,
            enforce_access_control=self.enforce_access_control,
        )

    def _build_document_extractor_skill(self) -> WebApiSkill:
        outputs = [
            OutputFieldMappingEntry(name="pages", target_name="pages"),
            OutputFieldMappingEntry(name="figures", target_name="figures"),
        ]

        return WebApiSkill(
            name=self.document_extractor.name,
            description=self.document_extractor.description,
            context="/document",
            uri=self.document_extractor.uri,
            http_method="POST",
            timeout=_DEFAULT_TIMEOUT,
            batch_size=_DEFAULT_BATCH_SIZE,
            degree_of_parallelism=1,
            # Managed identity: Search service authenticates against the function app using this resource ID.
            auth_resource_id=self.document_extractor.auth_resource_id,
            inputs=[
                InputFieldMappingEntry(name="blobUrl", source="/document/metadata_storage_path"),
                InputFieldMappingEntry(name="file_name", source="/document/metadata_storage_name"),
                InputFieldMappingEntry(name="content_type", source="/document/metadata_storage_content_type"),
                InputFieldMappingEntry(
                    name="metadata_storage_sas_token", source="/document/metadata_storage_sas_token"
                ),
            ],
            outputs=outputs,
        )

    def _build_figure_processor_skill(self) -> WebApiSkill:
        inputs = [
            InputFieldMappingEntry(name="figure_id", source="/document/figures/*/figure_id"),
            InputFieldMappingEntry(name="document_file_name", source="/document/figures/*/document_file_name"),
            InputFieldMappingEntry(name="filename", source="/document/figures/*/filename"),
            InputFieldMappingEntry(name="mime_type", source="/document/figures/*/mime_type"),
            InputFieldMappingEntry(name="bytes_base64", source="/document/figures/*/bytes_base64"),
            InputFieldMappingEntry(name="page_num", source="/document/figures/*/page_num"),
            InputFieldMappingEntry(name="bbox", source="/document/figures/*/bbox"),
        ]
        outputs = [
            OutputFieldMappingEntry(name="caption", target_name="caption"),
            OutputFieldMappingEntry(name="url", target_name="url"),
        ]
        if self.use_multimodal:
            outputs.append(OutputFieldMappingEntry(name="imageEmbedding", target_name="imageEmbedding"))

        return WebApiSkill(
            name=self.figure_processor.name,
            description=self.figure_processor.description,
            context="/document/figures/*",
            uri=self.figure_processor.uri,
            http_method="POST",
            timeout=_DEFAULT_TIMEOUT,
            batch_size=_DEFAULT_BATCH_SIZE,
            degree_of_parallelism=1,
            # Managed identity: Search service authenticates against the function app using this resource ID.
            auth_resource_id=self.figure_processor.auth_resource_id,
            inputs=inputs,
            outputs=outputs,
        )

    def _build_text_processor_skill(self) -> WebApiSkill:
        inputs = [
            InputFieldMappingEntry(name="pages", source="/document/pages"),
            InputFieldMappingEntry(name="figures", source="/document/figures"),
            InputFieldMappingEntry(name="file_name", source="/document/metadata_storage_name"),
            InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
        ]

        return WebApiSkill(
            name=self.text_processor.name,
            description=self.text_processor.description,
            context="/document",
            uri=self.text_processor.uri,
            http_method="POST",
            timeout=_DEFAULT_TIMEOUT,
            batch_size=_DEFAULT_BATCH_SIZE,
            degree_of_parallelism=1,
            # Managed identity: Search service authenticates against the function app using this resource ID.
            auth_resource_id=self.text_processor.auth_resource_id,
            inputs=inputs,
            outputs=[OutputFieldMappingEntry(name="chunks", target_name="chunks")],
        )

    def _build_skillset(self) -> SearchIndexerSkillset:
        mappings = [
            InputFieldMappingEntry(name="id", source="/document/chunks/*/id"),
            InputFieldMappingEntry(name="content", source="/document/chunks/*/content"),
            InputFieldMappingEntry(name="sourcepage", source="/document/chunks/*/sourcepage"),
            InputFieldMappingEntry(name="sourcefile", source="/document/chunks/*/sourcefile"),
            InputFieldMappingEntry(name=self.search_field_name_embedding, source="/document/chunks/*/embedding"),
            InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
        ]

        index_projection = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.search_info.index_name,
                    parent_key_field_name="parent_id",
                    source_context="/document/chunks/*",
                    mappings=mappings,
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS,
            ),
        )

        return SearchIndexerSkillset(
            name=self.skillset_name,
            description="Skillset linking document extraction, figure enrichment, and text processing functions",
            skills=[
                self._build_document_extractor_skill(),
                self._build_figure_processor_skill(),
                self._build_text_processor_skill(),
            ],
            index_projection=index_projection,
        )

    async def setup(self) -> None:
        logger.info("Setting up search index and skillset for cloud ingestion")
        self._search_manager = self._build_search_manager()
        await self._search_manager.create_index()

        async with self.search_info.create_search_indexer_client() as indexer_client:
            data_source_connection = SearchIndexerDataSourceConnection(
                name=self.data_source_name,
                type=SearchIndexerDataSourceType.AZURE_BLOB,
                connection_string=self.blob_manager.get_managedidentity_connectionstring(),
                container=SearchIndexerDataContainer(name=self.blob_manager.container),
                data_deletion_detection_policy=NativeBlobSoftDeleteDeletionDetectionPolicy(),
            )
            await indexer_client.create_or_update_data_source_connection(data_source_connection)

            skillset = self._build_skillset()
            await indexer_client.create_or_update_skillset(skillset)

    async def run(self) -> None:
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    await self.blob_manager.upload_blob(file)
                finally:
                    if file:
                        file.close()
        elif self.document_action == DocumentAction.Remove:
            paths = self.list_file_strategy.list_paths()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()

        indexer = SearchIndexer(
            name=self.indexer_name,
            description="Indexer orchestrating cloud ingestion pipeline",
            data_source_name=self.data_source_name,
            target_index_name=self.search_info.index_name,
            skillset_name=self.skillset_name,
        )

        async with self.search_info.create_search_indexer_client() as indexer_client:
            await indexer_client.create_or_update_indexer(indexer)
            await indexer_client.run_indexer(self.indexer_name)
        logger.info("Triggered indexer '%s' for cloud ingestion", self.indexer_name)
