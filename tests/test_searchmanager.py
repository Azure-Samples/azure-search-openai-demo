import io

import openai
import openai.types
import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    PermissionFilter,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexPermissionFilterOption,
    SimpleField,
    VectorSearch,
)
from openai.types.create_embedding_response import Usage

from prepdocslib.embeddings import OpenAIEmbeddings
from prepdocslib.listfilestrategy import File
from prepdocslib.page import ImageOnPage
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

    manager = SearchManager(search_info, use_parent_index_projection=False, field_name_embedding="embedding")
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
        use_parent_index_projection=True,
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
async def test_create_index_adds_vectorizer_to_existing_index(monkeypatch, search_info):
    """Test that a vectorizer is added to an existing index when embeddings are configured."""
    created_indexes = []
    updated_indexes = []

    async def mock_create_index(self, index):
        created_indexes.append(index)  # pragma: no cover

    async def mock_list_index_names(self):
        yield "test"

    async def mock_get_index(self, *args, **kwargs):
        # Return an existing index with vector_search but no vectorizers
        # Include embedding field to avoid triggering the embedding field addition code path
        return SearchIndex(
            name="test",
            fields=[
                SimpleField(
                    name="storageUrl",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SimpleField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=MOCK_EMBEDDING_DIMENSIONS,
                ),
            ],
            vector_search=VectorSearch(vectorizers=[]),
        )

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_indexes.append(index)

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    # Create a simple mock embeddings object with just the properties we need for index creation
    class MockEmbeddings:
        def __init__(self):
            self.azure_endpoint = "https://test.openai.azure.com"
            self.azure_deployment_name = "test-deployment"
            self.open_ai_model_name = MOCK_EMBEDDING_MODEL_NAME
            self.open_ai_dimensions = MOCK_EMBEDDING_DIMENSIONS

    embeddings = MockEmbeddings()

    manager = SearchManager(search_info, embeddings=embeddings, field_name_embedding="embedding")
    await manager.create_index()

    assert len(created_indexes) == 0, "It should not have created a new index"
    assert len(updated_indexes) == 1, "It should have updated the existing index"
    assert updated_indexes[0].vector_search.vectorizers is not None
    assert len(updated_indexes[0].vector_search.vectorizers) == 1, "Should have added one vectorizer"
    # The vectorizer name for updating existing indexes uses index_name
    assert updated_indexes[0].vector_search.vectorizers[0].vectorizer_name == "test-vectorizer"
    # Verify the vectorizer parameters
    vectorizer = updated_indexes[0].vector_search.vectorizers[0]
    assert vectorizer.parameters.resource_url == "https://test.openai.azure.com"
    assert vectorizer.parameters.deployment_name == "test-deployment"
    assert vectorizer.parameters.model_name == MOCK_EMBEDDING_MODEL_NAME


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
        enforce_access_control=True,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"
    assert indexes[0].permission_filter_option == SearchIndexPermissionFilterOption.ENABLED
    assert len(indexes[0].fields) == 8
    oids_field = next((field for field in indexes[0].fields if field.name == "oids"), None)
    assert oids_field is not None, "Expected 'oids' field to be present"
    assert oids_field.permission_filter == PermissionFilter.USER_IDS
    groups_field = next((field for field in indexes[0].fields if field.name == "groups"), None)
    assert groups_field is not None, "Expected 'groups' field to be present"
    assert groups_field.permission_filter == PermissionFilter.GROUP_IDS


@pytest.mark.asyncio
async def test_create_index_acls_no_enforcement(monkeypatch, search_info):
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
        enforce_access_control=False,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(indexes) == 1, "It should have created one index"
    assert indexes[0].name == "test"
    assert indexes[0].permission_filter_option == SearchIndexPermissionFilterOption.DISABLED
    assert len(indexes[0].fields) == 8
    oids_field = next((field for field in indexes[0].fields if field.name == "oids"), None)
    assert oids_field is not None, "Expected 'oids' field to be present"
    assert oids_field.permission_filter == PermissionFilter.USER_IDS
    groups_field = next((field for field in indexes[0].fields if field.name == "groups"), None)
    assert groups_field is not None, "Expected 'groups' field to be present"
    assert groups_field.permission_filter == PermissionFilter.GROUP_IDS


@pytest.mark.asyncio
async def test_create_index_acls_no_existing_fields(monkeypatch, search_info):
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

    manager = SearchManager(
        search_info,
        use_acls=True,
        enforce_access_control=True,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(updated_indexes) == 1, "It should have created one index"
    assert updated_indexes[0].name == "test"
    assert updated_indexes[0].permission_filter_option == SearchIndexPermissionFilterOption.ENABLED
    assert len(updated_indexes[0].fields) == 3
    oids_field = next((field for field in updated_indexes[0].fields if field.name == "oids"), None)
    assert oids_field is not None, "Expected 'oids' field to be present"
    assert oids_field.permission_filter == PermissionFilter.USER_IDS
    groups_field = next((field for field in updated_indexes[0].fields if field.name == "groups"), None)
    assert groups_field is not None, "Expected 'groups' field to be present"
    assert groups_field.permission_filter == PermissionFilter.GROUP_IDS


@pytest.mark.asyncio
async def test_create_index_acls_no_existing_fields_no_enforcement(monkeypatch, search_info):
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

    manager = SearchManager(
        search_info,
        use_acls=True,
        enforce_access_control=False,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(updated_indexes) == 1, "It should have created one index"
    assert updated_indexes[0].name == "test"
    assert updated_indexes[0].permission_filter_option == SearchIndexPermissionFilterOption.DISABLED
    assert len(updated_indexes[0].fields) == 3
    oids_field = next((field for field in updated_indexes[0].fields if field.name == "oids"), None)
    assert oids_field is not None, "Expected 'oids' field to be present"
    assert oids_field.permission_filter == PermissionFilter.USER_IDS
    groups_field = next((field for field in updated_indexes[0].fields if field.name == "groups"), None)
    assert groups_field is not None, "Expected 'groups' field to be present"
    assert groups_field.permission_filter == PermissionFilter.GROUP_IDS


@pytest.mark.asyncio
async def test_create_index_acls_with_existing_fields(monkeypatch, search_info):
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
                ),
                SimpleField(
                    name="oids",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                ),
                SimpleField(
                    name="groups",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                ),
            ],
        )

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_indexes.append(index)

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    manager = SearchManager(
        search_info,
        use_acls=True,
        enforce_access_control=True,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(updated_indexes) == 1, "It should have created one index"
    assert updated_indexes[0].name == "test"
    assert updated_indexes[0].permission_filter_option == SearchIndexPermissionFilterOption.ENABLED
    assert len(updated_indexes[0].fields) == 3
    oids_field = next((field for field in updated_indexes[0].fields if field.name == "oids"), None)
    assert oids_field is not None, "Expected 'oids' field to be present"
    assert oids_field.permission_filter == PermissionFilter.USER_IDS
    groups_field = next((field for field in updated_indexes[0].fields if field.name == "groups"), None)
    assert groups_field is not None, "Expected 'groups' field to be present"
    assert groups_field.permission_filter == PermissionFilter.GROUP_IDS


@pytest.mark.asyncio
async def test_create_index_acls_with_existing_fields_no_enforcement(monkeypatch, search_info):
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
                ),
                SimpleField(
                    name="oids",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                ),
                SimpleField(
                    name="groups",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True,
                ),
            ],
        )

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_indexes.append(index)

    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    manager = SearchManager(
        search_info,
        use_acls=True,
        enforce_access_control=False,
        field_name_embedding="embedding",
    )
    await manager.create_index()
    assert len(updated_indexes) == 1, "It should have created one index"
    assert updated_indexes[0].name == "test"
    assert updated_indexes[0].permission_filter_option == SearchIndexPermissionFilterOption.DISABLED
    assert len(updated_indexes[0].fields) == 3
    oids_field = next((field for field in updated_indexes[0].fields if field.name == "oids"), None)
    assert oids_field is not None, "Expected 'oids' field to be present"
    assert oids_field.permission_filter == PermissionFilter.USER_IDS
    groups_field = next((field for field in updated_indexes[0].fields if field.name == "groups"), None)
    assert groups_field is not None, "Expected 'groups' field to be present"
    assert groups_field.permission_filter == PermissionFilter.GROUP_IDS


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
    response = openai.types.CreateEmbeddingResponse(
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

    documents_uploaded = []

    async def mock_upload_documents(self, documents):
        documents_uploaded.extend(documents)

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(response)),
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        disable_batch=True,
        azure_deployment_name="x",
        azure_endpoint="https://x.openai.azure.com",
    )
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


@pytest.mark.asyncio
async def test_update_content_no_images_when_disabled(monkeypatch, search_info):
    """Ensure no 'images' field is added when search_images is False (baseline case without any images)."""

    documents_uploaded: list[dict] = []

    async def mock_upload_documents(self, documents):
        documents_uploaded.extend(documents)

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    manager = SearchManager(search_info, search_images=False)

    test_io = io.BytesIO(b"test file")
    test_io.name = "test/foo.pdf"
    file = File(test_io)

    section = Section(
        chunk=Chunk(page_num=0, text="chunk text"),
        content=file,
        category="test",
    )

    await manager.update_content([section])

    assert len(documents_uploaded) == 1, "Exactly one document should be uploaded"
    assert "images" not in documents_uploaded[0], "'images' field should not be present when search_images is False"


@pytest.mark.asyncio
async def test_update_content_with_images_when_enabled(monkeypatch, search_info):
    """Ensure 'images' field is added with image metadata when search_images is True and chunk has images."""

    documents_uploaded: list[dict] = []

    async def mock_upload_documents(self, documents):
        documents_uploaded.extend(documents)

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    # Enable image ingestion
    manager = SearchManager(search_info, search_images=True)

    test_io = io.BytesIO(b"img content")
    test_io.name = "test/foo.pdf"
    file = File(test_io)

    image = ImageOnPage(
        bytes=b"",  # raw image bytes not needed for this test
        bbox=(1.0, 2.0, 3.0, 4.0),
        filename="img1.png",
        description="Test image",
        figure_id="fig1",
        page_num=0,
        placeholder="<figure id='fig1'></figure>",
        url="http://example.com/img1.png",
        embedding=[0.01, 0.02],
    )

    section = Section(
        chunk=Chunk(page_num=0, text="chunk text with image", images=[image]),
        content=file,
        category="test",
    )

    await manager.update_content([section])

    assert len(documents_uploaded) == 1, "Exactly one document should be uploaded"
    doc = documents_uploaded[0]
    assert "images" in doc, "'images' field should be present when search_images is True"
    assert isinstance(doc["images"], list) and len(doc["images"]) == 1, "Should have one image entry"
    img_entry = doc["images"][0]
    assert img_entry["url"] == image.url
    assert img_entry["description"] == image.description
    assert img_entry["boundingbox"] == image.bbox
    assert img_entry["embedding"] == image.embedding


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
    response = openai.types.CreateEmbeddingResponse(
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
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(response)),
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        disable_batch=True,
        azure_deployment_name="x",
        azure_endpoint="https://x.openai.azure.com",
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


@pytest.mark.asyncio
async def test_create_knowledgebase_field_names_with_acls_and_images(monkeypatch, search_info):
    """Covers create_knowledgebase logic adding oids/groups/images and creating knowledge source (lines 443-447,449,457)."""

    # Provide a SearchInfo configured for agentic retrieval and image search
    search_info = SearchInfo(
        endpoint=search_info.endpoint,
        credential=search_info.credential,
        index_name=search_info.index_name,
        use_agentic_knowledgebase=True,
        knowledgebase_name="test-knowledgebase",
        azure_openai_knowledgebase_model="gpt-4o-mini",
        azure_openai_knowledgebase_deployment="gpt-4o-mini",
        azure_openai_endpoint="https://openaidummy.openai.azure.com/",
        azure_vision_endpoint="https://visiondummy.cognitiveservices.azure.com/",
    )

    created_indexes = []
    knowledge_sources = []
    knowledge_bases = []

    async def mock_list_index_names(self):
        for index in []:
            yield index  # pragma: no cover

    async def mock_create_index(self, index):
        created_indexes.append(index)

    async def mock_create_or_update_knowledge_source(self, knowledge_source, *args, **kwargs):
        knowledge_sources.append(knowledge_source)
        return knowledge_source

    async def mock_create_or_update_knowledge_base(self, knowledge_base, *args, **kwargs):
        knowledge_bases.append(knowledge_base)
        return knowledge_base

    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_knowledge_source", mock_create_or_update_knowledge_source)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_knowledge_base", mock_create_or_update_knowledge_base)

    manager = SearchManager(search_info, use_acls=True, search_images=True, use_web_source=True)

    # Act
    await manager.create_index()

    # Assert index created
    assert len(created_indexes) == 1, "Index should be created before Knowledge Base creation"
    # Assert index has images and ACL fields
    index = created_indexes[0]
    assert any(field.name == "images" for field in index.fields), "Index should have images field"
    assert any(field.name == "oids" for field in index.fields), "Index should have oids field"
    assert any(field.name == "groups" for field in index.fields), "Index should have groups field"

    # Assert knowledge sources were created (search index + web)
    assert len(knowledge_sources) == 2, "Two knowledge sources (search index and web) should be created"
    index_ks = next(ks for ks in knowledge_sources if hasattr(ks, "search_index_parameters"))
    selected = {field.name for field in index_ks.search_index_parameters.source_data_fields}
    for f in {"id", "sourcepage", "sourcefile", "content", "category", "oids", "groups", "images/url"}:
        assert f in selected, f"Missing field {f} in search index knowledge source selection"

    web_ks = next(ks for ks in knowledge_sources if not hasattr(ks, "search_index_parameters"))
    assert web_ks.name == "web", "Web knowledge source should use default naming"

    # Assert knowledge bases created for default and web-enabled variants
    assert len(knowledge_bases) == 2, "Base and web-enabled knowledge bases should be created"
    kb_by_name = {kb.name: kb for kb in knowledge_bases}
    assert set(kb_by_name) == {"test-knowledgebase", "test-knowledgebase-with-web"}

    default_kb_sources = {ref.name for ref in kb_by_name["test-knowledgebase"].knowledge_sources}
    assert default_kb_sources == {index_ks.name}, "Default knowledge base should reference only the index"

    web_kb_sources = {ref.name for ref in kb_by_name["test-knowledgebase-with-web"].knowledge_sources}
    assert {
        index_ks.name,
        web_ks.name,
    } == web_kb_sources, "Web-enabled knowledge base should reference index and web sources"


@pytest.mark.asyncio
async def test_create_knowledgebase_with_sharepoint_source(monkeypatch, search_info):
    """Test that SharePoint knowledge source is created when use_sharepoint_source=True."""

    # Provide a SearchInfo configured for agentic retrieval
    search_info = SearchInfo(
        endpoint=search_info.endpoint,
        credential=search_info.credential,
        index_name=search_info.index_name,
        use_agentic_knowledgebase=True,
        knowledgebase_name="test-knowledgebase",
        azure_openai_knowledgebase_model="gpt-4o-mini",
        azure_openai_knowledgebase_deployment="gpt-4o-mini",
        azure_openai_endpoint="https://openaidummy.openai.azure.com/",
    )

    created_indexes = []
    knowledge_sources = []
    knowledge_bases = []

    async def mock_list_index_names(self):
        for index in []:
            yield index  # pragma: no cover

    async def mock_create_index(self, index):
        created_indexes.append(index)

    async def mock_create_or_update_knowledge_source(self, knowledge_source, *args, **kwargs):
        knowledge_sources.append(knowledge_source)
        return knowledge_source

    async def mock_create_or_update_knowledge_base(self, knowledge_base, *args, **kwargs):
        knowledge_bases.append(knowledge_base)
        return knowledge_base

    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_knowledge_source", mock_create_or_update_knowledge_source)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_knowledge_base", mock_create_or_update_knowledge_base)

    manager = SearchManager(search_info, use_sharepoint_source=True)

    # Act
    await manager.create_index()

    # Assert index created
    assert len(created_indexes) == 1, "Index should be created before Knowledge Base creation"

    # Assert knowledge sources were created (search index + sharepoint)
    assert len(knowledge_sources) == 2, "Two knowledge sources (search index and sharepoint) should be created"
    index_ks = next(ks for ks in knowledge_sources if hasattr(ks, "search_index_parameters"))
    assert index_ks is not None, "Search index knowledge source should be created"

    sharepoint_ks = next(ks for ks in knowledge_sources if hasattr(ks, "remote_share_point_parameters"))
    assert sharepoint_ks.name == "sharepoint", "SharePoint knowledge source should use default naming"

    # Assert knowledge bases created for default and SharePoint-enabled variants
    assert len(knowledge_bases) == 2, "Base and SharePoint knowledge bases should be created"
    kb_by_name = {kb.name: kb for kb in knowledge_bases}
    assert set(kb_by_name) == {"test-knowledgebase", "test-knowledgebase-with-sp"}

    default_kb_sources = {ref.name for ref in kb_by_name["test-knowledgebase"].knowledge_sources}
    assert default_kb_sources == {index_ks.name}, "Default knowledge base should reference only the index"

    sharepoint_kb_sources = {ref.name for ref in kb_by_name["test-knowledgebase-with-sp"].knowledge_sources}
    assert {
        index_ks.name,
        sharepoint_ks.name,
    } == sharepoint_kb_sources, "SharePoint knowledge base should reference index and SharePoint sources"


@pytest.mark.asyncio
async def test_create_knowledgebase_with_web_and_sharepoint_sources(monkeypatch, search_info):
    """Verify all knowledge base variants exist when both optional sources are enabled."""

    search_info = SearchInfo(
        endpoint=search_info.endpoint,
        credential=search_info.credential,
        index_name=search_info.index_name,
        use_agentic_knowledgebase=True,
        knowledgebase_name="test-knowledgebase",
        azure_openai_knowledgebase_model="gpt-4o-mini",
        azure_openai_knowledgebase_deployment="gpt-4o-mini",
        azure_openai_endpoint="https://openaidummy.openai.azure.com/",
    )

    created_indexes = []
    knowledge_sources = []
    knowledge_bases = []

    async def mock_list_index_names(self):
        if False:
            yield  # pragma: no cover

    async def mock_create_index(self, index):
        created_indexes.append(index)

    async def mock_create_or_update_knowledge_source(self, knowledge_source, *args, **kwargs):
        knowledge_sources.append(knowledge_source)
        return knowledge_source

    async def mock_create_or_update_knowledge_base(self, knowledge_base, *args, **kwargs):
        knowledge_bases.append(knowledge_base)
        return knowledge_base

    monkeypatch.setattr(SearchIndexClient, "list_index_names", mock_list_index_names)
    monkeypatch.setattr(SearchIndexClient, "create_index", mock_create_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_knowledge_source", mock_create_or_update_knowledge_source)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_knowledge_base", mock_create_or_update_knowledge_base)

    manager = SearchManager(search_info, use_web_source=True, use_sharepoint_source=True)

    await manager.create_index()

    assert len(created_indexes) == 1, "Index should be created before knowledge base creation"
    index_ks = next(ks for ks in knowledge_sources if hasattr(ks, "search_index_parameters"))
    web_ks = next(ks for ks in knowledge_sources if getattr(ks, "name", None) == "web")
    sharepoint_ks = next(ks for ks in knowledge_sources if getattr(ks, "name", None) == "sharepoint")

    expected_kb_names = {
        "test-knowledgebase",
        "test-knowledgebase-with-web",
        "test-knowledgebase-with-sp",
        "test-knowledgebase-with-web-and-sp",
    }
    assert {kb.name for kb in knowledge_bases} == expected_kb_names

    kb_map = {kb.name: kb for kb in knowledge_bases}
    assert {ref.name for ref in kb_map["test-knowledgebase"].knowledge_sources} == {index_ks.name}
    assert {ref.name for ref in kb_map["test-knowledgebase-with-web"].knowledge_sources} == {index_ks.name, web_ks.name}
    assert {ref.name for ref in kb_map["test-knowledgebase-with-sp"].knowledge_sources} == {
        index_ks.name,
        sharepoint_ks.name,
    }
    assert {ref.name for ref in kb_map["test-knowledgebase-with-web-and-sp"].knowledge_sources} == {
        index_ks.name,
        web_ks.name,
        sharepoint_ks.name,
    }
