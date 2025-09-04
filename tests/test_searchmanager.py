import io

import openai
import openai.types
import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)
from openai.types.create_embedding_response import Usage

from prepdocslib.embeddings import AzureOpenAIEmbeddingService
from prepdocslib.listfilestrategy import File
from prepdocslib.searchmanager import SearchManager, Section
from prepdocslib.strategy import SearchInfo
from prepdocslib.textsplitter import Chunk

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
    MockClient,
    MockEmbeddingsClient,
)


@pytest.fixture
def search_info():
    return SearchInfo(
        endpoint="https://testsearchclient.blob.core.windows.net",
        credential=AzureKeyCredential("test"),
        index_name="test",
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

    manager = SearchManager(search_info, use_int_vectorization=False, field_name_embedding="embedding")
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

    manager = SearchManager(
        search_info,
        use_int_vectorization=True,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"
    assert len(indexes[0].fields) == 7


@pytest.mark.asyncio
async def test_create_index_does_exist(monkeypatch, search_info):
    created_indexes = []
    updated_indexes = []

    async def mock_create_index(self, index):
        created_indexes.append(index)

    async def mock_list_index_names(self):
        yield "test"

    async def mock_get_index(self, *args, **kwargs):
        return SearchIndex(
            name="test",
            fields=[
                SimpleField(
                    name="storageUrl",
                    type=SearchFieldDataType.String,
                    filterable=True,
                )
            ],
        )

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_indexes.append(index)

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    manager = SearchManager(search_info)
    await manager.create_index()
    assert len(created_indexes) == 0, "It should not have created a new index"
    assert len(updated_indexes) == 0, "It should not have updated the existing index"


@pytest.mark.asyncio
async def test_create_index_add_field(monkeypatch, search_info):
    created_indexes = []
    updated_indexes = []

    async def mock_create_index(self, index):
        created_indexes.append(index)

    async def mock_list_index_names(self):
        yield "test"

    async def mock_get_index(self, *args, **kwargs):
        return SearchIndex(
            name="test",
            fields=[],
        )

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_indexes.append(index)

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    manager = SearchManager(search_info)
    await manager.create_index()
    assert len(created_indexes) == 0, "It should not have created a new index"
    assert len(updated_indexes) == 1, "It should have updated the existing index"
    assert len(updated_indexes[0].fields) == 1
    assert updated_indexes[0].fields[0].name == "storageUrl"


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
        field_name_embedding="embedding",
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

    manager = SearchManager(search_info)

    test_io = io.BytesIO(b"test content")
    test_io.name = "test/foo.pdf"
    file = File(test_io)

    await manager.update_content(
        [
            Section(
                chunk=Chunk(
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

    manager = SearchManager(search_info)

    # create 1500 sections for 500 pages
    sections = []
    test_io = io.BytesIO(b"test page")
    test_io.name = "test/foo.pdf"
    file = File(test_io)
    for page_num in range(500):
        for page_section_num in range(3):
            sections.append(
                Section(
                    chunk=Chunk(
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
                    model="text-embedding-3-large",
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
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        open_ai_api_version="test-api-version",
        credential=AzureKeyCredential("test"),
        disable_batch=True,
    )
    monkeypatch.setattr(embeddings, "create_client", mock_create_client)
    manager = SearchManager(
        search_info,
        embeddings=embeddings,
        field_name_embedding="embedding3",
    )

    test_io = io.BytesIO(b"test content")
    test_io.name = "test/foo.pdf"
    file = File(test_io)

    await manager.update_content(
        [
            Section(
                chunk=Chunk(
                    page_num=0,
                    text="test content",
                ),
                content=file,
                category="test",
            )
        ]
    )

    assert len(documents_uploaded) == 1, "It should have uploaded one document"
    assert documents_uploaded[0]["embedding3"] == [
        0.0023064255,
        -0.009327292,
        -0.0028842222,
    ]


class AsyncSearchResultsIterator:
    def __init__(self, results):
        self.results = results

    def __aiter__(self):
        return self

    async def __anext__(self):
        if len(self.results) == 0:
            raise StopAsyncIteration
        return self.results.pop()

    async def get_count(self):
        return len(self.results)


@pytest.mark.asyncio
async def test_remove_content(monkeypatch, search_info):
    search_results = AsyncSearchResultsIterator(
        [
            {
                "@search.score": 1,
                "id": "file-foo_pdf-666F6F2E706466-page-0",
                "content": "test content",
                "category": "test",
                "sourcepage": "foo's bar.pdf#page=1",
                "sourcefile": "foo's bar.pdf",
            }
        ]
    )

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

    manager = SearchManager(search_info)

    await manager.remove_content("foo's bar.pdf")

    assert len(searched_filters) == 2, "It should have searched twice (with no results on second try)"
    assert searched_filters[0] == "sourcefile eq 'foo''s bar.pdf'"
    assert len(deleted_documents) == 1, "It should have deleted one document"
    assert deleted_documents[0]["id"] == "file-foo_pdf-666F6F2E706466-page-0"


@pytest.mark.asyncio
async def test_remove_content_no_docs(monkeypatch, search_info):

    search_results = AsyncSearchResultsIterator([])

    async def mock_search(self, *args, **kwargs):
        return search_results

    monkeypatch.setattr(SearchClient, "search", mock_search)

    deleted_calls = []

    async def mock_delete_documents(self, documents):
        deleted_calls.append(documents)
        return documents

    monkeypatch.setattr(SearchClient, "delete_documents", mock_delete_documents)

    manager = SearchManager(search_info)
    await manager.remove_content("foobar.pdf")

    assert len(deleted_calls) == 0, "It should have made zero calls to delete_documents"


@pytest.mark.asyncio
async def test_remove_content_only_oid(monkeypatch, search_info):
    search_results = AsyncSearchResultsIterator(
        [
            {
                "@search.score": 1,
                "id": "file-foo_pdf-666",
                "content": "test content",
                "category": "test",
                "sourcepage": "foo.pdf#page=1",
                "sourcefile": "foo.pdf",
                "oids": [],
            },
            {
                "@search.score": 1,
                "id": "file-foo_pdf-333",
                "content": "test content",
                "category": "test",
                "sourcepage": "foo.pdf#page=1",
                "sourcefile": "foo.pdf",
                "oids": ["A-USER-ID", "B-USER-ID"],
            },
            {
                "@search.score": 1,
                "id": "file-foo_pdf-222",
                "content": "test content",
                "category": "test",
                "sourcepage": "foo.pdf#page=1",
                "sourcefile": "foo.pdf",
                "oids": ["A-USER-ID"],
            },
        ]
    )

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

    manager = SearchManager(search_info)
    await manager.remove_content("foo.pdf", only_oid="A-USER-ID")

    assert len(searched_filters) == 2, "It should have searched twice (with no results on second try)"
    assert searched_filters[0] == "sourcefile eq 'foo.pdf'"
    assert len(deleted_documents) == 1, "It should have deleted one document"
    assert deleted_documents[0]["id"] == "file-foo_pdf-222"


@pytest.mark.asyncio
async def test_remove_content_no_inf_loop(monkeypatch, search_info):

    searched_filters = []

    async def mock_search(self, *args, **kwargs):
        self.filter = kwargs.get("filter")
        searched_filters.append(self.filter)
        return AsyncSearchResultsIterator(
            [
                {
                    "@search.score": 1,
                    "id": "file-foo_pdf-333",
                    "content": "test content",
                    "category": "test",
                    "sourcepage": "foo.pdf#page=1",
                    "sourcefile": "foo.pdf",
                    "oids": ["A-USER-ID", "B-USER-ID"],
                }
            ]
        )

    monkeypatch.setattr(SearchClient, "search", mock_search)

    deleted_documents = []

    async def mock_delete_documents(self, documents):
        deleted_documents.extend(documents)
        return documents

    monkeypatch.setattr(SearchClient, "delete_documents", mock_delete_documents)

    manager = SearchManager(search_info)
    await manager.remove_content("foo.pdf", only_oid="A-USER-ID")

    assert len(searched_filters) == 1, "It should have searched once"
    assert searched_filters[0] == "sourcefile eq 'foo.pdf'"
    assert len(deleted_documents) == 0, "It should have deleted no documents"


@pytest.mark.asyncio
async def test_create_index_with_search_images(monkeypatch, search_info):
    """Test that SearchManager correctly creates an index with image search capabilities."""
    indexes = []

    async def mock_create_index(self, index):
        indexes.append(index)

    async def mock_list_index_names(self):
        for index in []:
            yield index  # pragma: no cover

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)

    # Create a SearchInfo with an Azure Vision endpoint
    search_info_with_vision = SearchInfo(
        endpoint=search_info.endpoint,
        credential=search_info.credential,
        index_name=search_info.index_name,
        azure_vision_endpoint="https://testvision.cognitiveservices.azure.com/",
    )

    # Create a SearchManager with search_images=True
    manager = SearchManager(search_info_with_vision, search_images=True, field_name_embedding="embedding")
    await manager.create_index()

    # Verify the index was created correctly
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"

    # Find the "images" field in the index
    images_field = next((field for field in indexes[0].fields if field.name == "images"), None)
    assert images_field is not None, "The index should include an 'images' field"

    # Verify the "images" field structure
    assert images_field.type.startswith(
        "Collection(Edm.ComplexType)"
    ), "The 'images' field should be a collection of complex type"

    # Check subfields of the images field
    image_subfields = images_field.fields
    assert len(image_subfields) == 4, "The 'images' field should have 4 subfields"

    # Verify specific subfields
    assert any(field.name == "embedding" for field in image_subfields), "Should have an 'embedding' subfield"
    assert any(field.name == "url" for field in image_subfields), "Should have a 'url' subfield"
    assert any(field.name == "description" for field in image_subfields), "Should have a 'description' subfield"
    assert any(field.name == "boundingbox" for field in image_subfields), "Should have a 'boundingbox' subfield"

    # Verify vector search configuration
    vectorizers = indexes[0].vector_search.vectorizers
    assert any(
        v.vectorizer_name == "images-vision-vectorizer" for v in vectorizers
    ), "Should have an AI Vision vectorizer"

    # Verify vector search profile
    profiles = indexes[0].vector_search.profiles
    assert any(p.name == "images_embedding_profile" for p in profiles), "Should have an image embedding profile"


@pytest.mark.asyncio
async def test_create_index_with_search_images_no_endpoint(monkeypatch, search_info):
    """Test that SearchManager raises an error when search_images=True but no Azure Vision endpoint is provided."""

    # Create a SearchManager with search_images=True but no Azure Vision endpoint
    manager = SearchManager(
        search_info,  # search_info doesn't have azure_vision_endpoint
        search_images=True,
        field_name_embedding="embedding",
    )

    # Verify that create_index raises a ValueError
    with pytest.raises(ValueError) as excinfo:
        await manager.create_index()

    # Check the error message
    assert "Azure AI Vision endpoint must be provided to use image embeddings" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_index_with_search_images_and_embeddings(monkeypatch, search_info):
    """Test that SearchManager correctly creates an index with both image search and embeddings."""
    indexes = []

    async def mock_create_index(self, index):
        indexes.append(index)

    async def mock_list_index_names(self):
        for index in []:
            yield index  # pragma: no cover

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)

    # Create a SearchInfo with an Azure Vision endpoint
    search_info_with_vision = SearchInfo(
        endpoint=search_info.endpoint,
        credential=search_info.credential,
        index_name=search_info.index_name,
        azure_vision_endpoint="https://testvision.cognitiveservices.azure.com/",
    )

    # Create embeddings service
    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        open_ai_api_version="test-api-version",
        credential=AzureKeyCredential("test"),
        disable_batch=True,
    )

    # Create a SearchManager with both search_images and embeddings
    manager = SearchManager(
        search_info_with_vision, search_images=True, embeddings=embeddings, field_name_embedding="embedding3"
    )
    await manager.create_index()

    # Verify the index was created correctly
    assert len(indexes) == 1, "It should have created one index"

    # Find both the embeddings field and images field
    embedding_field = next((field for field in indexes[0].fields if field.name == "embedding3"), None)
    images_field = next((field for field in indexes[0].fields if field.name == "images"), None)

    assert embedding_field is not None, "The index should include an 'embedding3' field"
    assert images_field is not None, "The index should include an 'images' field"

    # Verify vector search configuration includes both text and image vectorizers
    vectorizers = indexes[0].vector_search.vectorizers
    assert any(
        v.vectorizer_name == "images-vision-vectorizer" for v in vectorizers
    ), "Should have an AI Vision vectorizer"
    assert any(hasattr(v, "ai_services_vision_parameters") for v in vectorizers), "Should have AI vision parameters"

    # Verify vector search profiles for both text and images
    profiles = indexes[0].vector_search.profiles
    assert any(p.name == "images_embedding_profile" for p in profiles), "Should have an image embedding profile"
    assert any(p.name == "embedding3-profile" for p in profiles), "Should have a text embedding profile"
