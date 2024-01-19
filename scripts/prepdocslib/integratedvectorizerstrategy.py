import datetime
import json
from enum import Enum
from typing import List, Optional

from azure.search.documents.indexes.models import (
    AzureOpenAIEmbeddingSkill,
    AzureOpenAIParameters,
    AzureOpenAIVectorizer,
    ExhaustiveKnnParameters,
    ExhaustiveKnnVectorSearchAlgorithmConfiguration,
    FieldMapping,
    HnswParameters,
    HnswVectorSearchAlgorithmConfiguration,
    IndexProjectionMode,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    PrioritizedFields,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataUserAssignedIdentity,
    SearchIndexerIndexProjections,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SplitSkill,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

from .blobmanager import BlobManager
from .embeddings import AzureOpenAIEmbeddingService
from .listfilestrategy import ListFileStrategy
from .pdfparser import PdfParser
from .searchmanager import SearchManager, Section
from .strategy import SearchInfo, Strategy
from .textsplitter import TextSplitter


class DocumentAction(Enum):
    Add = 0


class IntegratedVectorizerStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        embeddings: AzureOpenAIEmbeddingService,
        subscriptionId: str,
        searchServiceUserAssginedId: str,
        document_action: DocumentAction = DocumentAction.Add,
        search_analyzer_name: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.document_action = document_action
        self.embeddings = embeddings
        self.subscriptionId = subscriptionId
        self.search_user_assigned_identity = searchServiceUserAssginedId
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.category = category

    async def createEmbeddingSkill(self, index_name: str):
        skillset_name = f"{index_name}-skillset"

        split_skill = SplitSkill(
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

        openai_key = await self.embeddings.wrap_credential()

        embedding_skill = AzureOpenAIEmbeddingSkill(
            description="Skill to generate embeddings via Azure OpenAI",
            context="/document/pages/*",
            resource_uri=f"https://{self.embeddings.open_ai_service}.openai.azure.com",
            deployment_id=self.embeddings.open_ai_deployment,
            auth_identity=SearchIndexerDataUserAssignedIdentity(
                user_assigned_identity=f"/subscriptions/{self.subscriptionId}/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{self.search_user_assigned_identity}"
            ),
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/pages/*"),
            ],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="vector")],
        )

        index_projections = SearchIndexerIndexProjections(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=index_name,
                    parent_key_field_name="parent_id",
                    source_context="/document/pages/*",
                    mappings=[
                        InputFieldMappingEntry(name="content", source="/document/pages/*"),
                        InputFieldMappingEntry(name="embedding", source="/document/pages/*/vector"),
                        InputFieldMappingEntry(name="sourcefile", source="/document/metadata_storage_name"),
                    ],
                ),
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
            ),
        )

        skillset = SearchIndexerSkillset(
            name=skillset_name,
            description="Skillset to chunk documents and generating embeddings",
            skills=[split_skill, embedding_skill],
            index_projections=index_projections,
        )

        return skillset

    async def setup(self, search_info: SearchInfo):
        search_manager = SearchManager(
            search_info,
            self.search_analyzer_name,
            self.use_acls,
            self.embeddings,
            search_images=False,
        )
        await search_manager.create_index(
            [
                AzureOpenAIVectorizer(
                    name="myOpenAI",
                    kind="azureOpenAI",
                    azure_open_ai_parameters=AzureOpenAIParameters(
                        resource_uri=f"https://{self.embeddings.open_ai_service}.openai.azure.com",
                        deployment_id=self.embeddings.open_ai_deployment,
                        auth_identity=SearchIndexerDataUserAssignedIdentity(
                            user_assigned_identity=f"/subscriptions/{self.subscriptionId}/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{self.search_user_assigned_identity}"
                        ),
                    ),
                ),
            ]
        )

        # create indexer client
        ds_client = search_info.create_search_indexer_client()
        ds_container = SearchIndexerDataContainer(name=self.blob_manager.container)
        print(await self.blob_manager.get_blob_sas_365days())
        data_source_connection = SearchIndexerDataSourceConnection(
            name=f"{search_info.index_name}-blob",
            type="azureblob",
            connection_string=await self.blob_manager.get_blob_sas_365days(),
            container=ds_container,
        )
        data_source = await ds_client.create_or_update_data_source_connection(data_source_connection)

        embedding_skillset = await self.createEmbeddingSkill(search_info.index_name)
        await ds_client.create_or_update_skillset(embedding_skillset)

    async def run(self, search_info: SearchInfo):
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    blob_sas_uris = await self.blob_manager.upload_blob(file)
                finally:
                    if file:
                        file.close()

        # Create an indexer
        indexer_name = f"{search_info.index_name}-indexer"

        indexer = SearchIndexer(
            name=indexer_name,
            description="Indexer to index documents and generate embeddings",
            skillset_name=f"{search_info.index_name}-skillset",
            target_index_name=search_info.index_name,
            data_source_name=f"{search_info.index_name}-blob",
            # Map the metadata_storage_name field to the title field in the index to display the PDF title in the search results
            field_mappings=[FieldMapping(source_field_name="metadata_storage_name", target_field_name="title")],
        )

        indexer_client = search_info.create_search_indexer_client()

        indexer_result = await indexer_client.create_or_update_indexer(indexer)

        print(indexer_result)

        # Run the indexer
        await indexer_client.run_indexer(indexer_name)
