import asyncio
import logging
import os
from typing import Optional

from azure.search.documents.indexes.models import (
    AIServicesVisionParameters,
    AIServicesVisionVectorizer,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    BinaryQuantizationCompression,
    HnswAlgorithmConfiguration,
    HnswParameters,
    KnowledgeBase,
    KnowledgeBaseAzureOpenAIModel,
    KnowledgeRetrievalOutputMode,
    KnowledgeSourceReference,
    PermissionFilter,
    RemoteSharePointKnowledgeSource,
    RemoteSharePointKnowledgeSourceParameters,
    RescoringOptions,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexFieldReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
    SearchIndexPermissionFilterOption,
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
    WebKnowledgeSource,
)

from .blobmanager import BlobManager
from .embeddings import OpenAIEmbeddings
from .listfilestrategy import File
from .strategy import SearchInfo
from .textsplitter import Chunk

logger = logging.getLogger("scripts")


class Section:
    """
    A section of a page that is stored in a search service. These sections are used as context by Azure OpenAI service
    """

    def __init__(self, chunk: Chunk, content: File, category: Optional[str] = None):
        self.chunk = chunk  # content comes from here
        self.content = content  # sourcepage and sourcefile come from here
        self.category = category
        # this also needs images which will become the images field


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
        use_parent_index_projection: bool = False,
        embeddings: Optional[OpenAIEmbeddings] = None,
        field_name_embedding: Optional[str] = None,
        search_images: bool = False,
        enforce_access_control: bool = False,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False,
    ):
        self.search_info = search_info
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.use_parent_index_projection = use_parent_index_projection
        self.embeddings = embeddings
        self.embedding_dimensions = self.embeddings.open_ai_dimensions if self.embeddings else None
        self.field_name_embedding = field_name_embedding
        self.search_images = search_images
        self.enforce_access_control = enforce_access_control
        self.use_web_source = use_web_source
        self.use_sharepoint_source = use_sharepoint_source

    async def create_index(self):
        logger.info("Checking whether search index %s exists...", self.search_info.index_name)

        async with self.search_info.create_search_index_client() as search_index_client:
            embedding_field = None
            images_field = None
            text_vector_search_profile = None
            text_vector_algorithm = None
            text_vector_compression = None
            image_vector_search_profile = None
            image_vector_algorithm = None
            permission_filter_option = None

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
                if self.embeddings.azure_endpoint and self.embeddings.azure_deployment_name:
                    text_vectorizer = AzureOpenAIVectorizer(
                        vectorizer_name=f"{self.embeddings.open_ai_model_name}-vectorizer",
                        parameters=AzureOpenAIVectorizerParameters(
                            resource_url=self.embeddings.azure_endpoint,
                            deployment_name=self.embeddings.azure_deployment_name,
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
                if not self.search_info.azure_vision_endpoint:
                    raise ValueError("Azure AI Vision endpoint must be provided to use image embeddings")
                image_vector_algorithm = HnswAlgorithmConfiguration(
                    name="images_hnsw_config",
                    parameters=HnswParameters(metric="cosine"),
                )

                # Create the AI Vision vectorizer for image embeddings
                image_vectorizer = AIServicesVisionVectorizer(
                    vectorizer_name="images-vision-vectorizer",
                    ai_services_vision_parameters=AIServicesVisionParameters(
                        resource_uri=self.search_info.azure_vision_endpoint,
                        model_version="2023-04-15",
                    ),
                )

                image_vector_search_profile = VectorSearchProfile(
                    name="images_embedding_profile",
                    algorithm_configuration_name=image_vector_algorithm.name,
                    vectorizer_name=image_vectorizer.vectorizer_name,
                )
                images_field = SearchField(
                    name="images",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.ComplexType),
                    fields=[
                        SearchField(
                            name="embedding",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                            searchable=True,
                            stored=False,
                            vector_search_dimensions=1024,
                            vector_search_profile_name=image_vector_search_profile.name,
                        ),
                        SearchField(
                            name="url",
                            type=SearchFieldDataType.String,
                            searchable=False,
                            filterable=True,
                            sortable=False,
                            facetable=True,
                        ),
                        SearchField(
                            name="description",
                            type=SearchFieldDataType.String,
                            searchable=True,
                            filterable=False,
                            sortable=False,
                            facetable=False,
                        ),
                        SearchField(
                            name="boundingbox",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.Double),
                            searchable=False,
                            filterable=False,
                            sortable=False,
                            facetable=False,
                        ),
                    ],
                )

            if self.use_acls:
                oids_field = SearchField(
                    name="oids",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                    permission_filter=PermissionFilter.USER_IDS,
                )
                groups_field = SearchField(
                    name="groups",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                    permission_filter=PermissionFilter.GROUP_IDS,
                )

            if self.search_info.index_name not in [name async for name in search_index_client.list_index_names()]:
                logger.info("Creating new search index %s", self.search_info.index_name)
                fields = [
                    (
                        SimpleField(name="id", type="Edm.String", key=True)
                        if not self.use_parent_index_projection
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
                    fields.append(oids_field)
                    fields.append(groups_field)
                    permission_filter_option = (
                        SearchIndexPermissionFilterOption.ENABLED
                        if self.enforce_access_control
                        else SearchIndexPermissionFilterOption.DISABLED
                    )

                if self.use_parent_index_projection:
                    logger.info("Including parent_id field for parent/child index projection support in new index")
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

                if images_field:
                    logger.info("Including %s field for image descriptions and vectors in new index", images_field.name)
                    fields.append(images_field)
                    if image_vector_search_profile is None or image_vector_algorithm is None:
                        raise ValueError("Image search profile and algorithm must be set")
                    vector_search_profiles.append(image_vector_search_profile)
                    vector_algorithms.append(image_vector_algorithm)
                    # Add image vectorizer to vectorizers list
                    vectorizers.append(image_vectorizer)

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
                    permission_filter_option=permission_filter_option,
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
                    embedding_field.stored = True
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
                    # existing_index.vector_search.algorithms.append(text_vector_algorithm)
                    if existing_index.vector_search.compressions is None:
                        existing_index.vector_search.compressions = []
                    existing_index.vector_search.compressions.append(text_vector_compression)
                    await search_index_client.create_or_update_index(existing_index)

                if (
                    images_field
                    and images_field.fields
                    and not any(field.name == "images" for field in existing_index.fields)
                ):
                    logger.info("Adding %s field for image embeddings", images_field.name)
                    images_field.fields[0].stored = True
                    existing_index.fields.append(images_field)
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
                    if existing_index.vector_search.vectorizers is None:
                        existing_index.vector_search.vectorizers = []
                    existing_index.vector_search.vectorizers.append(image_vectorizer)
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
                    if (
                        self.embeddings is not None
                        and self.embeddings.azure_endpoint
                        and self.embeddings.azure_deployment_name
                    ):
                        logger.info("Adding vectorizer to search index %s", self.search_info.index_name)
                        existing_index.vector_search.vectorizers = [
                            AzureOpenAIVectorizer(
                                vectorizer_name=f"{self.search_info.index_name}-vectorizer",
                                parameters=AzureOpenAIVectorizerParameters(
                                    resource_url=self.embeddings.azure_endpoint,
                                    deployment_name=self.embeddings.azure_deployment_name,
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

                if self.use_acls:
                    if self.enforce_access_control:
                        logger.info("Enabling permission filtering on index %s", self.search_info.index_name)
                        existing_index.permission_filter_option = SearchIndexPermissionFilterOption.ENABLED
                    else:
                        logger.info("Disabling permission filtering on index %s", self.search_info.index_name)
                        existing_index.permission_filter_option = SearchIndexPermissionFilterOption.DISABLED

                    existing_oids_field = next((field for field in existing_index.fields if field.name == "oids"), None)
                    if existing_oids_field:
                        existing_oids_field.permission_filter = PermissionFilter.USER_IDS
                    else:
                        existing_index.fields.append(oids_field)
                    existing_groups_field = next(
                        (field for field in existing_index.fields if field.name == "groups"), None
                    )
                    if existing_groups_field:
                        existing_groups_field.permission_filter = PermissionFilter.GROUP_IDS
                    else:
                        existing_index.fields.append(groups_field)

                    await search_index_client.create_or_update_index(existing_index)

        if self.search_info.use_agentic_knowledgebase and self.search_info.knowledgebase_name:
            await self.create_knowledgebase()

    async def create_knowledgebase(self):
        """Creates one or more Knowledge Bases in the search index based on desired knowledge sources."""
        if self.search_info.knowledgebase_name:
            field_names = ["id", "sourcepage", "sourcefile", "content", "category"]
            if self.use_acls:
                field_names.extend(["oids", "groups"])
            if self.search_images:
                field_names.append("images/url")

            # Create field references using the new SDK pattern
            source_data_fields = [SearchIndexFieldReference(name=field) for field in field_names]

            async with self.search_info.create_search_index_client() as search_index_client:
                search_index_knowledge_source = SearchIndexKnowledgeSource(
                    name=self.search_info.index_name,  # Use the same name for convenience
                    description="Default knowledge source using the main search index",
                    search_index_parameters=SearchIndexKnowledgeSourceParameters(
                        search_index_name=self.search_info.index_name,
                        source_data_fields=source_data_fields,
                    ),
                )
                await search_index_client.create_or_update_knowledge_source(
                    knowledge_source=search_index_knowledge_source
                )

                knowledge_source_refs: dict[str, KnowledgeSourceReference] = {
                    "index": KnowledgeSourceReference(name=search_index_knowledge_source.name)
                }

                if self.use_web_source:
                    logger.info("Adding web knowledge source to the knowledge base")
                    web_knowledge_source = WebKnowledgeSource(
                        name="web"
                        # We do not specify a description here, since the default description is quite detailed already
                    )
                    await search_index_client.create_or_update_knowledge_source(knowledge_source=web_knowledge_source)
                    knowledge_source_refs["web"] = KnowledgeSourceReference(name=web_knowledge_source.name)

                if self.use_sharepoint_source:
                    logger.info("Adding SharePoint knowledge source to the knowledge base")
                    sharepoint_knowledge_source = RemoteSharePointKnowledgeSource(
                        name="sharepoint",
                        description="SharePoint knowledge source",
                        remote_share_point_parameters=RemoteSharePointKnowledgeSourceParameters(),
                    )
                    await search_index_client.create_or_update_knowledge_source(
                        knowledge_source=sharepoint_knowledge_source
                    )
                    knowledge_source_refs["sharepoint"] = KnowledgeSourceReference(
                        name=sharepoint_knowledge_source.name
                    )

                # Build the set of knowledge bases that should exist based on optional sources
                base_knowledgebase_name = self.search_info.knowledgebase_name
                knowledge_bases_to_upsert: list[tuple[str, list[KnowledgeSourceReference]]] = [
                    (base_knowledgebase_name, [knowledge_source_refs["index"]])
                ]

                if "web" in knowledge_source_refs:
                    knowledge_bases_to_upsert.append(
                        (
                            f"{base_knowledgebase_name}-with-web",
                            [knowledge_source_refs["index"], knowledge_source_refs["web"]],
                        )
                    )
                if "sharepoint" in knowledge_source_refs:
                    knowledge_bases_to_upsert.append(
                        (
                            f"{base_knowledgebase_name}-with-sp",
                            [knowledge_source_refs["index"], knowledge_source_refs["sharepoint"]],
                        )
                    )
                if "web" in knowledge_source_refs and "sharepoint" in knowledge_source_refs:
                    knowledge_bases_to_upsert.append(
                        (
                            f"{base_knowledgebase_name}-with-web-and-sp",
                            [
                                knowledge_source_refs["index"],
                                knowledge_source_refs["web"],
                                knowledge_source_refs["sharepoint"],
                            ],
                        )
                    )

                created_kb_names: list[str] = []
                for kb_name, sources in knowledge_bases_to_upsert:
                    logger.info("Creating (or updating) knowledge base '%s'...", kb_name)
                    await search_index_client.create_or_update_knowledge_base(
                        knowledge_base=KnowledgeBase(
                            name=kb_name,
                            knowledge_sources=sources,
                            models=[
                                KnowledgeBaseAzureOpenAIModel(
                                    azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                                        resource_url=self.search_info.azure_openai_endpoint,
                                        deployment_name=self.search_info.azure_openai_knowledgebase_deployment,
                                        model_name=self.search_info.azure_openai_knowledgebase_model,
                                    )
                                )
                            ],
                            output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
                        )
                    )
                    created_kb_names.append(kb_name)

            if created_kb_names:
                logger.info(
                    "Knowledge bases created successfully: %s",
                    ", ".join(created_kb_names),
                )

    async def update_content(self, sections: list[Section], url: Optional[str] = None):
        MAX_BATCH_SIZE = 1000
        section_batches = [sections[i : i + MAX_BATCH_SIZE] for i in range(0, len(sections), MAX_BATCH_SIZE)]

        async with self.search_info.create_search_client() as search_client:
            for batch_index, batch in enumerate(section_batches):
                documents = []
                for section_index, section in enumerate(batch):
                    image_fields = {}
                    if self.search_images:
                        image_fields = {
                            "images": [
                                {
                                    "url": image.url,
                                    "description": image.description,
                                    "boundingbox": image.bbox,
                                    "embedding": image.embedding,
                                }
                                for image in section.chunk.images
                            ]
                        }
                    document = {
                        "id": f"{section.content.filename_to_id()}-page-{section_index + batch_index * MAX_BATCH_SIZE}",
                        "content": section.chunk.text,
                        "category": section.category,
                        "sourcepage": BlobManager.sourcepage_from_file_page(
                            filename=section.content.filename(), page=section.chunk.page_num
                        ),
                        "sourcefile": section.content.filename(),
                        **image_fields,
                        **section.content.acls,
                    }
                    documents.append(document)
                if url:
                    for document in documents:
                        document["storageUrl"] = url
                if self.embeddings:
                    if self.field_name_embedding is None:
                        raise ValueError("Embedding field name must be set")
                    embeddings = await self.embeddings.create_embeddings(
                        texts=[section.chunk.text for section in batch]
                    )
                    for i, document in enumerate(documents):
                        document[self.field_name_embedding] = embeddings[i]
                logger.info(
                    "Uploading batch %d with %d sections to search index '%s'",
                    batch_index + 1,
                    len(documents),
                    self.search_info.index_name,
                )
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
