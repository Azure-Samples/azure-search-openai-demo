import asyncio
import logging
import os
from typing import Optional

from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    BinaryQuantizationCompression,
    HnswAlgorithmConfiguration,
    HnswParameters,
    KnowledgeAgent,
    KnowledgeAgentAzureOpenAIModel,
    KnowledgeAgentRequestLimits,
    KnowledgeAgentTargetIndex,
    RescoringOptions,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchCompression,
    VectorSearchCompressionRescoreStorageMethod,
    VectorSearchProfile,
    VectorSearchVectorizer,
)

from .blobmanager import BlobManager
from .embeddings import AzureOpenAIEmbeddingService, OpenAIEmbeddings
from .listfilestrategy import File
from .strategy import SearchInfo
from .textsplitter import SplitPage

logger = logging.getLogger("scripts")


class Section:
    """
    A section of a page that is stored in a search service. These sections are used as context by Azure OpenAI service
    """

    def __init__(self, split_page: SplitPage, content: File, category: Optional[str] = None):
        self.split_page = split_page
        self.content = content
        self.category = category


class SearchManager:
    """
    Class to manage a search service. It can create indexes, and update or remove sections stored in these indexes
    To learn more, please visit https://learn.microsoft.com/azure/search/search-what-is-azure-search
    """

    def __init__(
        self,
        search_info: SearchInfo,
        search_analyzer_name: Optional[str] = None,
        use_acls: bool = False,
        use_int_vectorization: bool = False,
        embeddings: Optional[OpenAIEmbeddings] = None,
        field_name_embedding: Optional[str] = None,
        search_images: bool = False,
    ):
        self.search_info = search_info
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.use_int_vectorization = use_int_vectorization
        self.embeddings = embeddings
        self.embedding_dimensions = self.embeddings.open_ai_dimensions if self.embeddings else None
        self.field_name_embedding = field_name_embedding
        self.search_images = search_images

    async def create_index(self):
        logger.info("Checking whether search index %s exists...", self.search_info.index_name)

        async with self.search_info.create_search_index_client() as search_index_client:

            embedding_field = None
            image_embedding_field = None
            text_vector_search_profile = None
            text_vector_algorithm = None
            text_vector_compression = None
            image_vector_search_profile = None
            image_vector_algorithm = None

            if self.embeddings:
                if self.embedding_dimensions is None:
                    raise ValueError(
                        "Embedding dimensions must be set in order to add an embedding field to the search index"
                    )
                if self.field_name_embedding is None:
                    raise ValueError(
                        "Embedding field must be set in order to add an embedding field to the search index"
                    )

                text_vectorizer = None
                if isinstance(self.embeddings, AzureOpenAIEmbeddingService):
                    text_vectorizer = AzureOpenAIVectorizer(
                        vectorizer_name=f"{self.embeddings.open_ai_model_name}-vectorizer",
                        parameters=AzureOpenAIVectorizerParameters(
                            resource_url=self.embeddings.open_ai_endpoint,
                            deployment_name=self.embeddings.open_ai_deployment,
                            model_name=self.embeddings.open_ai_model_name,
                        ),
                    )

                text_vector_algorithm = HnswAlgorithmConfiguration(
                    name="hnsw_config",
                    parameters=HnswParameters(metric="cosine"),
                )
                text_vector_compression = BinaryQuantizationCompression(
                    compression_name=f"{self.field_name_embedding}-compression",
                    truncation_dimension=1024,  # should this be a parameter? maybe not yet?
                    rescoring_options=RescoringOptions(
                        enable_rescoring=True,
                        default_oversampling=10,
                        rescore_storage_method=VectorSearchCompressionRescoreStorageMethod.PRESERVE_ORIGINALS,
                    ),
                    # Explicitly set deprecated parameters to None
                    rerank_with_original_vectors=None,
                    default_oversampling=None,
                )
                text_vector_search_profile = VectorSearchProfile(
                    name=f"{self.field_name_embedding}-profile",
                    algorithm_configuration_name=text_vector_algorithm.name,
                    compression_name=text_vector_compression.compression_name,
                    **({"vectorizer_name": text_vectorizer.vectorizer_name if text_vectorizer else None}),
                )

                embedding_field = SearchField(
                    name=self.field_name_embedding,
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    hidden=True,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=self.embedding_dimensions,
                    vector_search_profile_name=f"{self.field_name_embedding}-profile",
                    stored=False,
                )

            if self.search_images:
                image_vector_algorithm = HnswAlgorithmConfiguration(
                    name="image_hnsw_config",
                    parameters=HnswParameters(metric="cosine"),
                )
                image_vector_search_profile = VectorSearchProfile(
                    name="imageEmbedding-profile",
                    algorithm_configuration_name=image_vector_algorithm.name,
                )
                image_embedding_field = SearchField(
                    name="imageEmbedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    hidden=False,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=1024,
                    vector_search_profile_name=image_vector_search_profile.name,
                )

            if self.search_info.index_name not in [name async for name in search_index_client.list_index_names()]:
                logger.info("Creating new search index %s", self.search_info.index_name)
                fields = [
                    (
                        SimpleField(name="id", type="Edm.String", key=True)
                        if not self.use_int_vectorization
                        else SearchField(
                            name="id",
                            type="Edm.String",
                            key=True,
                            sortable=True,
                            filterable=True,
                            facetable=True,
                            analyzer_name="keyword",
                        )
                    ),
                    SearchableField(
                        name="content",
                        type="Edm.String",
                        analyzer_name=self.search_analyzer_name,
                    ),
                    SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                    SimpleField(
                        name="sourcepage",
                        type="Edm.String",
                        filterable=True,
                        facetable=True,
                    ),
                    SimpleField(
                        name="sourcefile",
                        type="Edm.String",
                        filterable=True,
                        facetable=True,
                    ),
                    SimpleField(
                        name="storageUrl",
                        type="Edm.String",
                        filterable=True,
                        facetable=False,
                    ),
                ]
                if self.use_acls:
                    fields.append(
                        SimpleField(
                            name="oids",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                            filterable=True,
                        )
                    )
                    fields.append(
                        SimpleField(
                            name="groups",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                            filterable=True,
                        )
                    )

                if self.use_int_vectorization:
                    logger.info("Including parent_id field for integrated vectorization support in new index")
                    fields.append(SearchableField(name="parent_id", type="Edm.String", filterable=True))

                vectorizers: list[VectorSearchVectorizer] = []
                vector_search_profiles = []
                vector_algorithms: list[VectorSearchAlgorithmConfiguration] = []
                vector_compressions: list[VectorSearchCompression] = []
                if embedding_field:
                    logger.info("Including %s field for text vectors in new index", embedding_field.name)
                    fields.append(embedding_field)
                    if text_vectorizer is not None:
                        vectorizers.append(text_vectorizer)
                    if (
                        text_vector_search_profile is None
                        or text_vector_algorithm is None
                        or text_vector_compression is None
                    ):
                        raise ValueError("Text vector search profile, algorithm and compression must be set")
                    vector_search_profiles.append(text_vector_search_profile)
                    vector_algorithms.append(text_vector_algorithm)
                    vector_compressions.append(text_vector_compression)

                if image_embedding_field:
                    logger.info("Including %s field for image vectors in new index", image_embedding_field.name)
                    fields.append(image_embedding_field)
                    if image_vector_search_profile is None or image_vector_algorithm is None:
                        raise ValueError("Image search profile and algorithm must be set")
                    vector_search_profiles.append(image_vector_search_profile)
                    vector_algorithms.append(image_vector_algorithm)

                index = SearchIndex(
                    name=self.search_info.index_name,
                    fields=fields,
                    semantic_search=SemanticSearch(
                        default_configuration_name="default",
                        configurations=[
                            SemanticConfiguration(
                                name="default",
                                prioritized_fields=SemanticPrioritizedFields(
                                    title_field=SemanticField(field_name="sourcepage"),
                                    content_fields=[SemanticField(field_name="content")],
                                ),
                            )
                        ],
                    ),
                    vector_search=VectorSearch(
                        profiles=vector_search_profiles,
                        algorithms=vector_algorithms,
                        compressions=vector_compressions,
                        vectorizers=vectorizers,
                    ),
                )

                await search_index_client.create_index(index)
            else:
                logger.info("Search index %s already exists", self.search_info.index_name)
                existing_index = await search_index_client.get_index(self.search_info.index_name)
                if not any(field.name == "storageUrl" for field in existing_index.fields):
                    logger.info("Adding storageUrl field to index %s", self.search_info.index_name)
                    existing_index.fields.append(
                        SimpleField(
                            name="storageUrl",
                            type="Edm.String",
                            filterable=True,
                            facetable=False,
                        ),
                    )
                    await search_index_client.create_or_update_index(existing_index)

                if embedding_field and not any(
                    field.name == self.field_name_embedding for field in existing_index.fields
                ):
                    logger.info("Adding %s field for text embeddings", self.field_name_embedding)
                    existing_index.fields.append(embedding_field)
                    if existing_index.vector_search is None:
                        raise ValueError("Vector search is not enabled for the existing index")
                    if text_vectorizer is not None:
                        if existing_index.vector_search.vectorizers is None:
                            existing_index.vector_search.vectorizers = []
                        existing_index.vector_search.vectorizers.append(text_vectorizer)
                    if (
                        text_vector_search_profile is None
                        or text_vector_algorithm is None
                        or text_vector_compression is None
                    ):
                        raise ValueError("Text vector search profile, algorithm and compression must be set")
                    if existing_index.vector_search.profiles is None:
                        existing_index.vector_search.profiles = []
                    existing_index.vector_search.profiles.append(text_vector_search_profile)
                    if existing_index.vector_search.algorithms is None:
                        existing_index.vector_search.algorithms = []
                    existing_index.vector_search.algorithms.append(text_vector_algorithm)
                    if existing_index.vector_search.compressions is None:
                        existing_index.vector_search.compressions = []
                    existing_index.vector_search.compressions.append(text_vector_compression)
                    await search_index_client.create_or_update_index(existing_index)

                if image_embedding_field and not any(field.name == "imageEmbedding" for field in existing_index.fields):
                    logger.info("Adding %s field for image embeddings", image_embedding_field.name)
                    existing_index.fields.append(image_embedding_field)
                    if image_vector_search_profile is None or image_vector_algorithm is None:
                        raise ValueError("Image vector search profile and algorithm must be set")
                    if existing_index.vector_search is None:
                        raise ValueError("Image vector search is not enabled for the existing index")
                    if existing_index.vector_search.profiles is None:
                        existing_index.vector_search.profiles = []
                    existing_index.vector_search.profiles.append(image_vector_search_profile)
                    if existing_index.vector_search.algorithms is None:
                        existing_index.vector_search.algorithms = []
                    existing_index.vector_search.algorithms.append(image_vector_algorithm)
                    await search_index_client.create_or_update_index(existing_index)

                if existing_index.semantic_search:
                    if not existing_index.semantic_search.default_configuration_name:
                        logger.info("Adding default semantic configuration to index %s", self.search_info.index_name)
                        existing_index.semantic_search.default_configuration_name = "default"

                    if existing_index.semantic_search.configurations:
                        existing_semantic_config = existing_index.semantic_search.configurations[0]
                        if (
                            existing_semantic_config.prioritized_fields
                            and existing_semantic_config.prioritized_fields.title_field
                            and not existing_semantic_config.prioritized_fields.title_field.field_name == "sourcepage"
                        ):
                            logger.info("Updating semantic configuration for index %s", self.search_info.index_name)
                            existing_semantic_config.prioritized_fields.title_field = SemanticField(
                                field_name="sourcepage"
                            )

                if existing_index.vector_search is not None and (
                    existing_index.vector_search.vectorizers is None
                    or len(existing_index.vector_search.vectorizers) == 0
                ):
                    if self.embeddings is not None and isinstance(self.embeddings, AzureOpenAIEmbeddingService):
                        logger.info("Adding vectorizer to search index %s", self.search_info.index_name)
                        existing_index.vector_search.vectorizers = [
                            AzureOpenAIVectorizer(
                                vectorizer_name=f"{self.search_info.index_name}-vectorizer",
                                parameters=AzureOpenAIVectorizerParameters(
                                    resource_url=self.embeddings.open_ai_endpoint,
                                    deployment_name=self.embeddings.open_ai_deployment,
                                    model_name=self.embeddings.open_ai_model_name,
                                ),
                            )
                        ]
                        await search_index_client.create_or_update_index(existing_index)

                    else:
                        logger.info(
                            "Can't add vectorizer to search index %s since no Azure OpenAI embeddings service is defined",
                            self.search_info,
                        )
        if self.search_info.use_agentic_retrieval and self.search_info.agent_name:
            await self.create_agent()

    async def create_agent(self):
        if self.search_info.agent_name:
            logger.info(f"Creating search agent named {self.search_info.agent_name}")

            async with self.search_info.create_search_index_client() as search_index_client:
                await search_index_client.create_or_update_agent(
                    agent=KnowledgeAgent(
                        name=self.search_info.agent_name,
                        target_indexes=[
                            KnowledgeAgentTargetIndex(
                                index_name=self.search_info.index_name, default_include_reference_source_data=True
                            )
                        ],
                        models=[
                            KnowledgeAgentAzureOpenAIModel(
                                azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                                    resource_url=self.search_info.azure_openai_endpoint,
                                    deployment_name=self.search_info.azure_openai_searchagent_deployment,
                                    model_name=self.search_info.azure_openai_searchagent_model,
                                )
                            )
                        ],
                        request_limits=KnowledgeAgentRequestLimits(
                            max_output_size=self.search_info.agent_max_output_tokens
                        ),
                    )
                )

            logger.info("Agent %s created successfully", self.search_info.agent_name)

    async def update_content(
        self, sections: list[Section], image_embeddings: Optional[list[list[float]]] = None, url: Optional[str] = None
    ):
        MAX_BATCH_SIZE = 1000
        section_batches = [sections[i : i + MAX_BATCH_SIZE] for i in range(0, len(sections), MAX_BATCH_SIZE)]

        async with self.search_info.create_search_client() as search_client:
            for batch_index, batch in enumerate(section_batches):
                documents = [
                    {
                        "id": f"{section.content.filename_to_id()}-page-{section_index + batch_index * MAX_BATCH_SIZE}",
                        "content": section.split_page.text,
                        "category": section.category,
                        "sourcepage": (
                            BlobManager.blob_image_name_from_file_page(
                                filename=section.content.filename(),
                                page=section.split_page.page_num,
                            )
                            if image_embeddings
                            else BlobManager.sourcepage_from_file_page(
                                filename=section.content.filename(),
                                page=section.split_page.page_num,
                            )
                        ),
                        "sourcefile": section.content.filename(),
                        **section.content.acls,
                    }
                    for section_index, section in enumerate(batch)
                ]
                if url:
                    for document in documents:
                        document["storageUrl"] = url
                if self.embeddings:
                    if self.field_name_embedding is None:
                        raise ValueError("Embedding field name must be set")
                    embeddings = await self.embeddings.create_embeddings(
                        texts=[section.split_page.text for section in batch]
                    )
                    for i, document in enumerate(documents):
                        document[self.field_name_embedding] = embeddings[i]
                if image_embeddings:
                    for i, (document, section) in enumerate(zip(documents, batch)):
                        document["imageEmbedding"] = image_embeddings[section.split_page.page_num]

                await search_client.upload_documents(documents)

    async def remove_content(self, path: Optional[str] = None, only_oid: Optional[str] = None):
        logger.info(
            "Removing sections from '{%s or '<all>'}' from search index '%s'", path, self.search_info.index_name
        )
        async with self.search_info.create_search_client() as search_client:
            while True:
                filter = None
                if path is not None:
                    # Replace ' with '' to escape the single quote for the filter
                    # https://learn.microsoft.com/azure/search/query-odata-filter-orderby-syntax#escaping-special-characters-in-string-constants
                    path_for_filter = os.path.basename(path).replace("'", "''")
                    filter = f"sourcefile eq '{path_for_filter}'"
                max_results = 1000
                result = await search_client.search(
                    search_text="", filter=filter, top=max_results, include_total_count=True
                )
                result_count = await result.get_count()
                if result_count == 0:
                    break
                documents_to_remove = []
                async for document in result:
                    # If only_oid is set, only remove documents that have only this oid
                    if not only_oid or document.get("oids") == [only_oid]:
                        documents_to_remove.append({"id": document["id"]})
                if len(documents_to_remove) == 0:
                    if result_count < max_results:
                        break
                    else:
                        continue
                removed_docs = await search_client.delete_documents(documents_to_remove)
                logger.info("Removed %d sections from index", len(removed_docs))
                # It can take a few seconds for search results to reflect changes, so wait a bit
                await asyncio.sleep(2)
