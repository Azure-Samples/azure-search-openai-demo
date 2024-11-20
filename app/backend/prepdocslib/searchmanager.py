import asyncio
import datetime
import logging
import os
from typing import List, Optional

import dateutil.parser as parser
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    HnswParameters,
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
        search_images: bool = False,
    ):
        self.search_info = search_info
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.use_int_vectorization = use_int_vectorization
        self.embeddings = embeddings
        # Integrated vectorization uses the ada-002 model with 1536 dimensions
        self.embedding_dimensions = self.embeddings.open_ai_dimensions if self.embeddings else 1536
        self.search_images = search_images

    async def create_index(self, vectorizers: Optional[List[VectorSearchVectorizer]] = None):
        logger.info("Checking whether search index %s exists...", self.search_info.index_name)

        async with self.search_info.create_search_index_client() as search_index_client:
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
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    hidden=False,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=self.embedding_dimensions,
                    vector_search_profile_name="embedding_config",
                ),
                SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="md5", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="deeplink", type="Edm.String", filterable=True, facetable=False),
                SimpleField(name="updated", type="Edm.DateTimeOffset", filterable=True, facetable=True),
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
                logger.info("Including parent_id field in new index %s", self.search_info.index_name)
                fields.append(SearchableField(name="parent_id", type="Edm.String", filterable=True))
            if self.search_images:
                logger.info("Including imageEmbedding field in new index %s", self.search_info.index_name)
                fields.append(
                    SearchField(
                        name="imageEmbedding",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        hidden=False,
                        searchable=True,
                        filterable=False,
                        sortable=False,
                        facetable=False,
                        vector_search_dimensions=1024,
                        vector_search_profile_name="embedding_config",
                    ),
                )

            if self.search_info.index_name not in [name async for name in search_index_client.list_index_names()]:
                logger.info("Creating new search index %s", self.search_info.index_name)

                vectorizers = []
                if self.embeddings and isinstance(self.embeddings, AzureOpenAIEmbeddingService):
                    logger.info(
                        "Including vectorizer for search index %s, using Azure OpenAI service %s",
                        self.search_info.index_name,
                        self.embeddings.open_ai_service,
                    )
                    vectorizers.append(
                        AzureOpenAIVectorizer(
                            vectorizer_name=f"{self.search_info.index_name}-vectorizer",
                            parameters=AzureOpenAIVectorizerParameters(
                                resource_url=self.embeddings.open_ai_endpoint,
                                deployment_name=self.embeddings.open_ai_deployment,
                                model_name=self.embeddings.open_ai_model_name,
                            ),
                        )
                    )
                else:
                    logger.info(
                        "Not including vectorizer for search index %s, no Azure OpenAI service found",
                        self.search_info.index_name,
                    )

                index = SearchIndex(
                    name=self.search_info.index_name,
                    fields=fields,
                    semantic_search=SemanticSearch(
                        configurations=[
                            SemanticConfiguration(
                                name="default",
                                prioritized_fields=SemanticPrioritizedFields(
                                    title_field=None, content_fields=[SemanticField(field_name="content")]
                                ),
                            )
                        ]
                    ),
                    vector_search=VectorSearch(
                        algorithms=[
                            HnswAlgorithmConfiguration(
                                name="hnsw_config",
                                parameters=HnswParameters(metric="cosine"),
                            )
                        ],
                        profiles=[
                            VectorSearchProfile(
                                name="embedding_config",
                                algorithm_configuration_name="hnsw_config",
                                vectorizer_name=(
                                    f"{self.search_info.index_name}-vectorizer" if self.use_int_vectorization else None
                                ),
                            ),
                        ],
                        vectorizers=vectorizers,
                    ),
                )

                await search_index_client.create_index(index)
            else:
                logger.info("Search index %s already exists", self.search_info.index_name)
                existing_index = await search_index_client.get_index(self.search_info.index_name)
                existing_field_names = {field.name for field in existing_index.fields}

                # Check and add missing fields
                missing_fields = [field for field in fields if field.name not in existing_field_names]
                if missing_fields:
                    logger.info(
                        "Adding missing fields to index %s: %s",
                        self.search_info.index_name,
                        [field.name for field in missing_fields],
                    )
                    existing_index.fields.extend(missing_fields)
                    await search_index_client.create_or_update_index(existing_index)

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

    async def file_exists(self, file: File) -> bool:
        async with self.search_info.create_search_client() as search_client:
            ## make sure that we don't update unchanged sections, by if sourcefile and md5 are the same
            if file.metadata.get("md5") is not None:
                filter = None
                assert file.filename() is not None
                filter = f"sourcefile eq '{str(file.filename())}'  and md5 eq '{file.metadata.get('md5')}'"

                # make sure (when applicable) that we don't skip if different categories have same file.filename()
                # TODO: refactoring: check if using file.filename() as primary for blob is a good idea, or better use sha256(instead as md5) as reliable  for blob and index primary key
                if file.metadata.get("category") is not None:
                    filter = filter + f" and category eq '{file.metadata.get('category')}'"
                max_results = 1
                result = await search_client.search(
                    search_text="", filter=filter, top=max_results, include_total_count=True
                )
                result_count = await result.get_count()
                if result_count > 0:
                    logger.debug("Skipping %s, no changes detected.", file.filename())
                    return True
                else:
                    return False
            ## -- end of check

    async def update_content(
        self, sections: List[Section], file: File, image_embeddings: Optional[List[List[float]]] = None
    ):
        MAX_BATCH_SIZE = 1000
        section_batches = [sections[i : i + MAX_BATCH_SIZE] for i in range(0, len(sections), MAX_BATCH_SIZE)]

        async with self.search_info.create_search_client() as search_client:

            ## caluclate a (default) updated timestamp in format of index
            if file.metadata.get("updated") is None:
                docdate = datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            else:
                docdate = parser.isoparse(file.metadata.get("updated")).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            for batch_index, batch in enumerate(section_batches):
                documents = [
                    {
                        "id": f"{section.content.filename_to_id()}-page-{section_index + batch_index * MAX_BATCH_SIZE}",
                        "content": section.split_page.text,
                        "category": file.metadata.get("category"),
                        "md5": file.metadata.get("md5"),
                        "deeplink": file.metadata.get(
                            "deeplink"
                        ),  # optional deel link original doc source for citiation,inline view
                        "updated": docdate,
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
                if file.url:
                    for document in documents:
                        document["storageUrl"] = file.url
                if self.embeddings:
                    embeddings = await self.embeddings.create_embeddings(
                        texts=[section.split_page.text for section in batch]
                    )
                    for i, document in enumerate(documents):
                        document["embedding"] = embeddings[i]
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
