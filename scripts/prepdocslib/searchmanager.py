import asyncio
import os
from typing import List, Optional

from azure.search.documents.indexes.models import (
    HnswParameters,
    PrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
)

from .blobmanager import BlobManager
from .embeddings import OpenAIEmbeddings
from .listfilestrategy import File
from .strategy import SearchInfo
from .textsplitter import SplitPage


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
        embeddings: Optional[OpenAIEmbeddings] = None,
    ):
        self.search_info = search_info
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.embeddings = embeddings

    async def create_index(self):
        if self.search_info.verbose:
            print(f"Ensuring search index {self.search_info.index_name} exists")

        async with self.search_info.create_search_index_client() as search_index_client:
            fields = [
                SimpleField(name="id", type="Edm.String", key=True),
                SearchableField(name="content", type="Edm.String", analyzer_name=self.search_analyzer_name),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    hidden=False,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=1536,
                    vector_search_configuration="default",
                ),
                SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcepage", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcefile", type="Edm.String", filterable=True, facetable=True),
            ]
            if self.use_acls:
                fields.append(
                    SimpleField(
                        name="oids", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True
                    )
                )
                fields.append(
                    SimpleField(
                        name="groups", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True
                    )
                )

            index = SearchIndex(
                name=self.search_info.index_name,
                fields=fields,
                semantic_settings=SemanticSettings(
                    configurations=[
                        SemanticConfiguration(
                            name="default",
                            prioritized_fields=PrioritizedFields(
                                title_field=None, prioritized_content_fields=[SemanticField(field_name="content")]
                            ),
                        )
                    ]
                ),
                vector_search=VectorSearch(
                    algorithm_configurations=[
                        VectorSearchAlgorithmConfiguration(
                            name="default", kind="hnsw", hnsw_parameters=HnswParameters(metric="cosine")
                        )
                    ]
                ),
            )
            if self.search_info.index_name not in [name async for name in search_index_client.list_index_names()]:
                if self.search_info.verbose:
                    print(f"Creating {self.search_info.index_name} search index")
                await search_index_client.create_index(index)
            else:
                if self.search_info.verbose:
                    print(f"Search index {self.search_info.index_name} already exists")

    async def update_content(self, sections: List[Section]):
        MAX_BATCH_SIZE = 1000
        section_batches = [sections[i : i + MAX_BATCH_SIZE] for i in range(0, len(sections), MAX_BATCH_SIZE)]

        async with self.search_info.create_search_client() as search_client:
            for batch in section_batches:
                documents = [
                    {
                        "id": f"{section.content.filename_to_id()}-page-{i}",
                        "content": section.split_page.text,
                        "category": section.category,
                        "sourcepage": BlobManager.sourcepage_from_file_page(
                            filename=section.content.filename(), page=section.split_page.page_num
                        ),
                        "sourcefile": section.content.filename(),
                        **section.content.acls,
                    }
                    for i, section in enumerate(batch)
                ]
                if self.embeddings:
                    embeddings = await self.embeddings.create_embeddings(
                        texts=[section.split_page.text for section in batch]
                    )
                    for i, document in enumerate(documents):
                        document["embedding"] = embeddings[i]

                await search_client.upload_documents(documents)

    async def remove_content(self, path: Optional[str] = None):
        if self.search_info.verbose:
            print(f"Removing sections from '{path or '<all>'}' from search index '{self.search_info.index_name}'")
        async with self.search_info.create_search_client() as search_client:
            while True:
                filter = None if path is None else f"sourcefile eq '{os.path.basename(path)}'"
                result = await search_client.search("", filter=filter, top=1000, include_total_count=True)
                if await result.get_count() == 0:
                    break
                removed_docs = await search_client.delete_documents(
                    documents=[{"id": document["id"]} async for document in result]
                )
                if self.search_info.verbose:
                    print(f"\tRemoved {len(removed_docs)} sections from index")
                # It can take a few seconds for search results to reflect changes, so wait a bit
                await asyncio.sleep(2)
