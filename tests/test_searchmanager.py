import io

import openai
import openai.types
import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from openai.types.create_embedding_response import Usage

from scripts.prepdocslib.embeddings import AzureOpenAIEmbeddingService
from scripts.prepdocslib.listfilestrategy import File
from scripts.prepdocslib.searchmanager import SearchManager, Section
from scripts.prepdocslib.strategy import SearchInfo
from scripts.prepdocslib.textsplitter import SplitPage


class MockEmbeddingsClient:
    def __init__(self, create_embedding_response: openai.types.CreateEmbeddingResponse):
        self.create_embedding_response = create_embedding_response

    async def create(self, *args, **kwargs) -> openai.types.CreateEmbeddingResponse:
        return self.create_embedding_response


class MockClient:
    def __init__(self, embeddings_client):
        self.embeddings = embeddings_client


@pytest.fixture
def search_info():
    return SearchInfo(
        endpoint="https://testsearchclient.blob.core.windows.net",
        credential=AzureKeyCredential("test"),
        index_name="test",
        verbose=True,
    )


@pytest.mark.asyncio
async def test_create_index_doesnt_exist_yet(monkeypatch, search_info):
    indexes = []

    async def mock_create_index(self, index):
        indexes.append(index)

    async def mock_list_index_names(self):
        for index in []:
            yield index

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)

    manager = SearchManager(
        search_info,
    )
    await manager.create_index()
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"
    assert len(indexes[0].fields) == 6


@pytest.mark.asyncio
async def test_create_index_using_int_vectorization(monkeypatch, search_info):
    indexes = []

    async def mock_create_index(self, index):
        indexes.append(index)

    async def mock_list_index_names(self):
        for index in []:
            yield index

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)

    manager = SearchManager(search_info, use_int_vectorization=True)
    await manager.create_index()
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"
    assert len(indexes[0].fields) == 7


@pytest.mark.asyncio
async def test_create_index_does_exist(monkeypatch, search_info):
    indexes = []

    async def mock_create_index(self, index):
        indexes.append(index)

    async def mock_list_index_names(self):
        yield "test"

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)

    manager = SearchManager(
        search_info,
    )
    await manager.create_index()
    assert len(indexes) == 0, "It should not have created a new index"


@pytest.mark.asyncio
async def test_create_index_acls(monkeypatch, search_info):
    indexes = []

    async def mock_create_index(self, index):
        indexes.append(index)

    async def mock_list_index_names(self):
        for index in []:
            yield index

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)

    manager = SearchManager(
        search_info,
        use_acls=True,
    )
    await manager.create_index()
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"
    assert len(indexes[0].fields) == 8


@pytest.mark.asyncio
async def test_update_content(monkeypatch, search_info):
    async def mock_upload_documents(self, documents):
        assert len(documents) == 1
        assert documents[0]["id"] == "file-foo_pdf-666F6F2E706466-page-0"
        assert documents[0]["content"] == "test content"
        assert documents[0]["category"] == "test"
        assert documents[0]["sourcepage"] == "foo.pdf#page=1"
        assert documents[0]["sourcefile"] == "foo.pdf"

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    manager = SearchManager(
        search_info,
    )

    test_io = io.BytesIO(b"test content")
    test_io.name = "test/foo.pdf"
    file = File(test_io)

    await manager.update_content(
        [
            Section(
                split_page=SplitPage(
                    page_num=0,
                    text="test content",
                ),
                content=file,
                category="test",
            )
        ]
    )


@pytest.mark.asyncio
async def test_update_content_many(monkeypatch, search_info):
    ids = []

    async def mock_upload_documents(self, documents):
        ids.extend([doc["id"] for doc in documents])

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    manager = SearchManager(
        search_info,
    )

    # create 1500 sections for 500 pages
    sections = []
    test_io = io.BytesIO(b"test page")
    test_io.name = "test/foo.pdf"
    file = File(test_io)
    for page_num in range(500):
        for page_section_num in range(3):
            sections.append(
                Section(
                    split_page=SplitPage(
                        page_num=page_num,
                        text=f"test section {page_section_num}",
                    ),
                    content=file,
                    category="test",
                )
            )

    await manager.update_content(sections)

    assert len(ids) == 1500, "Wrong number of documents uploaded"
    assert len(set(ids)) == 1500, "Document ids are not unique"


@pytest.mark.asyncio
async def test_update_content_with_embeddings(monkeypatch, search_info):
    async def mock_create_client(*args, **kwargs):
        # From https://platform.openai.com/docs/api-reference/embeddings/create
        return MockClient(
            embeddings_client=MockEmbeddingsClient(
                create_embedding_response=openai.types.CreateEmbeddingResponse(
                    object="list",
                    data=[
                        openai.types.Embedding(
                            embedding=[
                                0.0023064255,
                                -0.009327292,
                                -0.0028842222,
                            ],
                            index=0,
                            object="embedding",
                        )
                    ],
                    model="text-embedding-ada-002",
                    usage=Usage(prompt_tokens=8, total_tokens=8),
                )
            )
        )

    documents_uploaded = []

    async def mock_upload_documents(self, documents):
        documents_uploaded.extend(documents)

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)
    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name="text-ada-003",
        credential=AzureKeyCredential("test"),
        disable_batch=True,
    )
    monkeypatch.setattr(embeddings, "create_client", mock_create_client)
    manager = SearchManager(
        search_info,
        embeddings=embeddings,
    )

    test_io = io.BytesIO(b"test content")
    test_io.name = "test/foo.pdf"
    file = File(test_io)

    await manager.update_content(
        [
            Section(
                split_page=SplitPage(
                    page_num=0,
                    text="test content",
                ),
                content=file,
                category="test",
            )
        ]
    )

    assert len(documents_uploaded) == 1, "It should have uploaded one document"
    assert documents_uploaded[0]["embedding"] == [
        0.0023064255,
        -0.009327292,
        -0.0028842222,
    ]


@pytest.mark.asyncio
async def test_remove_content(monkeypatch, search_info):
    class AsyncSearchResultsIterator:
        def __init__(self):
            self.results = [
                {
                    "@search.score": 1,
                    "id": "file-foo_pdf-666F6F2E706466-page-0",
                    "content": "test content",
                    "category": "test",
                    "sourcepage": "foo.pdf#page=1",
                    "sourcefile": "foo.pdf",
                }
            ]

        def __aiter__(self):
            return self

        async def __anext__(self):
            if len(self.results) == 0:
                raise StopAsyncIteration
            return self.results.pop()

        async def get_count(self):
            return len(self.results)

    search_results = AsyncSearchResultsIterator()

    searched_filters = []

    async def mock_search(self, *args, **kwargs):
        self.filter = kwargs.get("filter")
        searched_filters.append(self.filter)
        return search_results

    monkeypatch.setattr(SearchClient, "search", mock_search)

    deleted_documents = []

    async def mock_delete_documents(self, documents):
        deleted_documents.extend(documents)
        return documents

    monkeypatch.setattr(SearchClient, "delete_documents", mock_delete_documents)

    manager = SearchManager(
        search_info,
    )

    await manager.remove_content("foo.pdf")

    assert len(searched_filters) == 2, "It should have searched twice (with no results on second try)"
    assert searched_filters[0] == "sourcefile eq 'foo.pdf'"
    assert len(deleted_documents) == 1, "It should have deleted one document"
    assert deleted_documents[0]["id"] == "file-foo_pdf-666F6F2E706466-page-0"
