import logging
from typing import Optional

from azure.search.documents.indexes._generated.models import (
    NativeBlobSoftDeleteDeletionDetectionPolicy,
)
from azure.search.documents.indexes.models import (
    AzureOpenAIEmbeddingSkill,
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
    SplitSkill,
)

from .blobmanager import BlobManager
from .embeddings import AzureOpenAIEmbeddingService
from .listfilestrategy import ListFileStrategy
from .searchmanager import SearchManager
from .strategy import DocumentAction, SearchInfo, Strategy

logger = logging.getLogger("scripts")


class IntegratedVectorizerStrategy(Strategy):
    """
    Strategy for ingesting and vectorizing documents into a search service from files stored storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        embeddings: AzureOpenAIEmbeddingService,
        search_field_name_embedding: str,
        subscription_id: str,
        search_service_user_assigned_id: str,
        document_action: DocumentAction = DocumentAction.Add,
        search_analyzer_name: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
    ):

        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.document_action = document_action
        self.embeddings = embeddings
        self.search_field_name_embedding = search_field_name_embedding
        self.subscription_id = subscription_id
        self.search_user_assigned_identity = search_service_user_assigned_id
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.category = category
        self.search_info = search_info
        prefix = f"{self.search_info.index_name}-{self.search_field_name_embedding}"
        self.skillset_name = f"{prefix}-skillset"
        self.indexer_name = f"{prefix}-indexer"
        self.data_source_name = f"{prefix}-blob"

    async def create_embedding_skill(self, index_name: str) -> SearchIndexerSkillset:
        """
        Create a skillset for the indexer to chunk documents and generate embeddings
        """

        split_skill = SplitSkill(
            name="split-skill",
            description="Split skill to chunk documents",
            text_split_mode="pages",
            context="/document",
            maximum_page_length=2048,
            page_overlap_length=20,
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/content"),
            ],
            outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")],
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            name="embedding-skill",
            description="Skill to generate embeddings via Azure OpenAI",
            context="/document/pages/*",
            resource_url=f"https://{self.embeddings.open_ai_service}.openai.azure.com",
            deployment_name=self.embeddings.open_ai_deployment,
            model_name=self.embeddings.open_ai_model_name,
            dimensions=self.embeddings.open_ai_dimensions,
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/pages/*"),
            ],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="vector")],
        )

        index_projection = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=index_name,
                    parent_key_field_name="parent_id",
                    source_context="/document/pages/*",
                    mappings=[
                        InputFieldMappingEntry(name="content", source="/document/pages/*"),
                        InputFieldMappingEntry(name="sourcepage", source="/document/metadata_storage_name"),
                        InputFieldMappingEntry(name="sourcefile", source="/document/metadata_storage_name"),
                        InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
                        InputFieldMappingEntry(
                            name=self.search_field_name_embedding, source="/document/pages/*/vector"
                        ),
                    ],
                ),
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
            ),
        )

        skillset = SearchIndexerSkillset(
            name=self.skillset_name,
            description="Skillset to chunk documents and generate embeddings",
            skills=[split_skill, embedding_skill],
            index_projection=index_projection,
        )

        return skillset

    async def setup(self):
        logger.info("Setting up search index using integrated vectorization...")
        search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=self.search_analyzer_name,
            use_acls=self.use_acls,
            use_int_vectorization=True,
            embeddings=self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=False,
        )

        await search_manager.create_index()

        ds_client = self.search_info.create_search_indexer_client()
        ds_container = SearchIndexerDataContainer(name=self.blob_manager.container)
        data_source_connection = SearchIndexerDataSourceConnection(
            name=self.data_source_name,
            type=SearchIndexerDataSourceType.AZURE_BLOB,
            connection_string=self.blob_manager.get_managedidentity_connectionstring(),
            container=ds_container,
            data_deletion_detection_policy=NativeBlobSoftDeleteDeletionDetectionPolicy(),
        )

        await ds_client.create_or_update_data_source_connection(data_source_connection)

        embedding_skillset = await self.create_embedding_skill(self.search_info.index_name)
        await ds_client.create_or_update_skillset(embedding_skillset)
        await ds_client.close()

    async def run(self):
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

        # Create an indexer
        indexer = SearchIndexer(
            name=self.indexer_name,
            description="Indexer to index documents and generate embeddings",
            skillset_name=self.skillset_name,
            target_index_name=self.search_info.index_name,
            data_source_name=self.data_source_name,
        )

        indexer_client = self.search_info.create_search_indexer_client()
        indexer_result = await indexer_client.create_or_update_indexer(indexer)

        # Run the indexer
        await indexer_client.run_indexer(self.indexer_name)
        await indexer_client.close()

        logger.info(
            f"Successfully created index, indexer: {indexer_result.name}, and skillset. Please navigate to search service in Azure Portal to view the status of the indexer."
        )
