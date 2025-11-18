"""Cloud ingestion strategy using Azure AI Search custom skills."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from azure.search.documents.indexes._generated.models import (
    NativeBlobSoftDeleteDeletionDetectionPolicy,
)
from azure.search.documents.indexes.models import (
    IndexingParameters,
    IndexingParametersConfiguration,
    IndexProjectionMode,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataSourceType,
    SearchIndexerDataUserAssignedIdentity,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    ShaperSkill,
    WebApiSkill,
)

from .blobmanager import BlobManager
from .embeddings import OpenAIEmbeddings
from .listfilestrategy import ListFileStrategy
from .searchmanager import SearchManager
from .strategy import DocumentAction, SearchInfo, Strategy

logger = logging.getLogger("scripts")

DEFAULT_SKILL_TIMEOUT = timedelta(seconds=230)
DEFAULT_BATCH_SIZE = 1


@dataclass(slots=True)
class SkillConfig:
    """Configuration for a custom Web API skill."""

    name: str
    description: str
    uri: str
    auth_resource_id: str


class CloudIngestionStrategy(Strategy):  # pragma: no cover
    """Ingestion strategy that wires Azure Function custom skills into an indexer."""

    def __init__(
        self,
        *,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        embeddings: OpenAIEmbeddings,
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
        use_web_source: bool = False,
        search_user_assigned_identity_resource_id: str,
    ) -> None:
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
        self.use_web_source = use_web_source
        self.subscription_id = subscription_id

        prefix = f"{self.search_info.index_name}-cloud"
        self.skillset_name = f"{prefix}-skillset"
        self.indexer_name = f"{prefix}-indexer"
        self.data_source_name = f"{prefix}-blob"

        self.document_extractor = SkillConfig(
            name=f"{prefix}-document-extractor-skill",
            description="Custom skill that downloads and parses source documents",
            uri=document_extractor_uri,
            auth_resource_id=document_extractor_auth_resource_id,
        )
        self.figure_processor = SkillConfig(
            name=f"{prefix}-figure-processor-skill",
            description="Custom skill that enriches individual figures",
            uri=figure_processor_uri,
            auth_resource_id=figure_processor_auth_resource_id,
        )
        self.text_processor = SkillConfig(
            name=f"{prefix}-text-processor-skill",
            description="Custom skill that merges figures, chunks text, and generates embeddings",
            uri=text_processor_uri,
            auth_resource_id=text_processor_auth_resource_id,
        )

        self._search_manager: SearchManager | None = None
        self.search_user_assigned_identity_resource_id = search_user_assigned_identity_resource_id

    def _build_skillset(self) -> SearchIndexerSkillset:
        prefix = f"{self.search_info.index_name}-cloud"

        # NOTE: Do NOT map the chunk id directly to the index key field. Azure AI Search
        # index projections forbid mapping an input field onto the target index key when
        # using parent/child projections. The service will generate keys for projected
        # child documents automatically. Removing the explicit 'id' mapping resolves
        # HttpResponseError: "Input 'id' cannot map to the key field".
        mappings = [
            InputFieldMappingEntry(name="content", source="/document/chunks/*/content"),
            InputFieldMappingEntry(name="sourcepage", source="/document/chunks/*/sourcepage"),
            InputFieldMappingEntry(name="sourcefile", source="/document/chunks/*/sourcefile"),
            InputFieldMappingEntry(name=self.search_field_name_embedding, source="/document/chunks/*/embedding"),
            InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
        ]
        if self.use_multimodal:
            mappings.append(InputFieldMappingEntry(name="images", source="/document/chunks/*/images"))

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

        document_extractor_skill = WebApiSkill(
            name=self.document_extractor.name,
            description=self.document_extractor.description,
            context="/document",
            uri=self.document_extractor.uri,
            http_method="POST",
            timeout=DEFAULT_SKILL_TIMEOUT,
            batch_size=DEFAULT_BATCH_SIZE,
            degree_of_parallelism=1,
            # Managed identity: Search service authenticates against the function app using this resource ID.
            auth_resource_id=self.document_extractor.auth_resource_id,
            auth_identity=SearchIndexerDataUserAssignedIdentity(
                resource_id=self.search_user_assigned_identity_resource_id
            ),
            inputs=[
                # Provide the binary payload expected by the document extractor custom skill.
                InputFieldMappingEntry(name="file_data", source="/document/file_data"),
                InputFieldMappingEntry(name="file_name", source="/document/metadata_storage_name"),
                InputFieldMappingEntry(name="content_type", source="/document/metadata_storage_content_type"),
            ],
            outputs=[
                OutputFieldMappingEntry(name="pages", target_name="pages"),
                OutputFieldMappingEntry(name="figures", target_name="figures"),
            ],
        )

        figure_processor_skill = WebApiSkill(
            name=self.figure_processor.name,
            description=self.figure_processor.description,
            context="/document/figures/*",
            uri=self.figure_processor.uri,
            http_method="POST",
            timeout=DEFAULT_SKILL_TIMEOUT,
            batch_size=DEFAULT_BATCH_SIZE,
            degree_of_parallelism=1,
            # Managed identity: Search service authenticates against the function app using this resource ID.
            auth_resource_id=self.figure_processor.auth_resource_id,
            auth_identity=SearchIndexerDataUserAssignedIdentity(
                resource_id=self.search_user_assigned_identity_resource_id
            ),
            inputs=[
                InputFieldMappingEntry(name="figure_id", source="/document/figures/*/figure_id"),
                InputFieldMappingEntry(name="document_file_name", source="/document/figures/*/document_file_name"),
                InputFieldMappingEntry(name="filename", source="/document/figures/*/filename"),
                InputFieldMappingEntry(name="mime_type", source="/document/figures/*/mime_type"),
                InputFieldMappingEntry(name="bytes_base64", source="/document/figures/*/bytes_base64"),
                InputFieldMappingEntry(name="page_num", source="/document/figures/*/page_num"),
                InputFieldMappingEntry(name="bbox", source="/document/figures/*/bbox"),
                InputFieldMappingEntry(name="placeholder", source="/document/figures/*/placeholder"),
                InputFieldMappingEntry(name="title", source="/document/figures/*/title"),
            ],
            outputs=[
                # Only output the enriched fields to avoid cyclic dependency
                OutputFieldMappingEntry(name="description", target_name="description"),
                OutputFieldMappingEntry(name="url", target_name="url"),
                OutputFieldMappingEntry(name="embedding", target_name="embedding"),
            ],
        )

        # Shaper skill to consolidate pages and enriched figures into a single object
        shaper_skill = ShaperSkill(
            name=f"{prefix}-document-shaper-skill",
            description="Consolidates pages and enriched figures into a single document object",
            context="/document",
            inputs=[
                InputFieldMappingEntry(name="pages", source="/document/pages"),
                InputFieldMappingEntry(
                    name="figures",
                    source_context="/document/figures/*",
                    inputs=[
                        InputFieldMappingEntry(name="figure_id", source="/document/figures/*/figure_id"),
                        InputFieldMappingEntry(
                            name="document_file_name", source="/document/figures/*/document_file_name"
                        ),
                        InputFieldMappingEntry(name="filename", source="/document/figures/*/filename"),
                        InputFieldMappingEntry(name="mime_type", source="/document/figures/*/mime_type"),
                        InputFieldMappingEntry(name="page_num", source="/document/figures/*/page_num"),
                        InputFieldMappingEntry(name="bbox", source="/document/figures/*/bbox"),
                        InputFieldMappingEntry(name="placeholder", source="/document/figures/*/placeholder"),
                        InputFieldMappingEntry(name="title", source="/document/figures/*/title"),
                        InputFieldMappingEntry(name="description", source="/document/figures/*/description"),
                        InputFieldMappingEntry(name="url", source="/document/figures/*/url"),
                        InputFieldMappingEntry(name="embedding", source="/document/figures/*/embedding"),
                    ],
                ),
                InputFieldMappingEntry(name="file_name", source="/document/metadata_storage_name"),
                InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
            ],
            outputs=[OutputFieldMappingEntry(name="output", target_name="consolidated_document")],
        )

        text_processor_skill = WebApiSkill(
            name=self.text_processor.name,
            description=self.text_processor.description,
            context="/document",
            uri=self.text_processor.uri,
            http_method="POST",
            timeout=DEFAULT_SKILL_TIMEOUT,
            batch_size=DEFAULT_BATCH_SIZE,
            degree_of_parallelism=1,
            # Managed identity: Search service authenticates against the function app using this resource ID.
            auth_resource_id=self.text_processor.auth_resource_id,
            auth_identity=SearchIndexerDataUserAssignedIdentity(
                resource_id=self.search_user_assigned_identity_resource_id
            ),
            inputs=[
                InputFieldMappingEntry(name="consolidated_document", source="/document/consolidated_document"),
            ],
            outputs=[OutputFieldMappingEntry(name="chunks", target_name="chunks")],
        )

        return SearchIndexerSkillset(
            name=self.skillset_name,
            description="Skillset linking document extraction, figure enrichment, and text processing functions",
            skills=[document_extractor_skill, figure_processor_skill, shaper_skill, text_processor_skill],
            index_projection=index_projection,
        )

    async def setup(self) -> None:
        logger.info("Setting up search index and skillset for cloud ingestion")

        if not self.embeddings.azure_endpoint or not self.embeddings.azure_deployment_name:
            raise ValueError("Cloud ingestion requires Azure OpenAI endpoint and deployment")

        if not isinstance(self.embeddings, OpenAIEmbeddings):
            raise TypeError("Cloud ingestion requires Azure OpenAI embeddings to configure the search index.")

        self._search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=self.search_analyzer_name,
            use_acls=self.use_acls,
            use_parent_index_projection=True,
            embeddings=self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.use_multimodal,
            enforce_access_control=self.enforce_access_control,
            use_web_source=self.use_web_source,
        )

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

            indexer = SearchIndexer(
                name=self.indexer_name,
                description="Indexer orchestrating cloud ingestion pipeline",
                data_source_name=self.data_source_name,
                target_index_name=self.search_info.index_name,
                skillset_name=self.skillset_name,
                parameters=IndexingParameters(
                    configuration=IndexingParametersConfiguration(
                        query_timeout=None,  # type: ignore
                        data_to_extract="storageMetadata",
                        allow_skillset_to_read_file_data=True,
                    )
                ),
            )
            await indexer_client.create_or_update_indexer(indexer)

    async def run(self) -> None:
        files = self.list_file_strategy.list()
        async for file in files:
            try:
                await self.blob_manager.upload_blob(file)
            finally:
                if file:
                    file.close()

        async with self.search_info.create_search_indexer_client() as indexer_client:
            await indexer_client.run_indexer(self.indexer_name)
        logger.info("Triggered indexer '%s' for cloud ingestion", self.indexer_name)
