from io import BytesIO

import azure.core.exceptions
import azure.storage.filedatalake
import azure.storage.filedatalake.aio
import pytest
from azure.search.documents.aio import SearchClient
from azure.storage.filedatalake.aio import DataLakeDirectoryClient, DataLakeFileClient
from openai.types.create_embedding_response import (
    CreateEmbeddingResponse,
    Embedding,
    Usage,
)
from quart.datastructures import FileStorage

from prepdocslib.embeddings import AzureOpenAIEmbeddingService

from .mocks import MockClient, MockEmbeddingsClient


# parameterize for directory existing or not
@pytest.mark.asyncio
@pytest.mark.parametrize("directory_exists", [True, False])
async def test_upload_file(auth_client, monkeypatch, mock_data_lake_service_client, directory_exists):

    async def mock_get_directory_properties(self, *args, **kwargs):
        if directory_exists:
            return None
        else:
            raise azure.core.exceptions.ResourceNotFoundError()

    monkeypatch.setattr(DataLakeDirectoryClient, "get_directory_properties", mock_get_directory_properties)

    directory_created = [False]

    async def mock_create_directory(self, *args, **kwargs):
        directory_created[0] = True

    monkeypatch.setattr(DataLakeDirectoryClient, "create_directory", mock_create_directory)

    async def mock_directory_set_access_control(self, *args, **kwargs):
        assert kwargs.get("owner") == "OID_X"
        return None

    monkeypatch.setattr(DataLakeDirectoryClient, "set_access_control", mock_directory_set_access_control)

    def mock_directory_get_file_client(self, *args, **kwargs):
        path = kwargs.get("file")
        if path in self.files:
            return self.files[path]
        self.files[path] = DataLakeFileClient(path)
        return self.files[path]

    monkeypatch.setattr(DataLakeDirectoryClient, "get_file_client", mock_directory_get_file_client)

    async def mock_upload_file(self, *args, **kwargs):
        assert kwargs.get("overwrite") is True
        assert kwargs.get("metadata") == {"UploadedBy": "OID_X"}
        return None

    monkeypatch.setattr(DataLakeFileClient, "upload_data", mock_upload_file)

    async def mock_create_client(self, *args, **kwargs):
        # From https://platform.openai.com/docs/api-reference/embeddings/create
        return MockClient(
            embeddings_client=MockEmbeddingsClient(
                create_embedding_response=CreateEmbeddingResponse(
                    object="list",
                    data=[
                        Embedding(
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
    monkeypatch.setattr(AzureOpenAIEmbeddingService, "create_client", mock_create_client)

    response = await auth_client.post(
        "/upload",
        headers={"Authorization": "Bearer test"},
        files={"file": FileStorage(BytesIO(b"foo;bar"), filename="a.txt")},
    )
    message = (await response.get_json())["message"]
    assert message == "File uploaded successfully"
    assert response.status_code == 200
    assert len(documents_uploaded) == 1
    assert documents_uploaded[0]["id"] == "file-a_txt-612E7478747B276F696473273A205B274F49445F58275D7D-page-0"
    assert documents_uploaded[0]["sourcepage"] == "a.txt"
    assert documents_uploaded[0]["sourcefile"] == "a.txt"
    assert documents_uploaded[0]["embedding"] == [0.0023064255, -0.009327292, -0.0028842222]
    assert documents_uploaded[0]["category"] is None
    assert documents_uploaded[0]["oids"] == ["OID_X"]
    assert directory_created[0] == (not directory_exists)


@pytest.mark.asyncio
async def test_list_uploaded(auth_client, monkeypatch, mock_data_lake_service_client):
    response = await auth_client.get("/list_uploaded", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert (await response.get_json()) == ["a.txt", "b.txt", "c.txt"]


@pytest.mark.asyncio
async def test_list_uploaded_nopaths(auth_client, monkeypatch, mock_data_lake_service_client):
    class MockResponse:
        def __init__(self):
            self.reason = "No path found"
            self.status_code = 404

    class MockAsyncIteratorError:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise azure.core.exceptions.ResourceNotFoundError(
                response=azure.core.exceptions.HttpResponseError(response=MockResponse())
            )

    def mock_get_paths(self, *args, **kwargs):
        return MockAsyncIteratorError()

    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "get_paths", mock_get_paths)

    response = await auth_client.get("/list_uploaded", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert (await response.get_json()) == []


@pytest.mark.asyncio
async def test_delete_uploaded(auth_client, monkeypatch, mock_data_lake_service_client):

    async def mock_delete_file(self):
        return None

    monkeypatch.setattr(DataLakeFileClient, "delete_file", mock_delete_file)

    class AsyncSearchResultsIterator:
        def __init__(self):
            self.results = [
                {
                    "sourcepage": "a.txt",
                    "sourcefile": "a.txt",
                    "content": "This is a test document.",
                    "embedding": [],
                    "category": None,
                    "id": "file-a_txt-7465737420646F63756D656E742E706466",
                    "oids": ["OID_X"],
                    "@search.score": 0.03279569745063782,
                    "@search.reranker_score": 3.4577205181121826,
                },
                {
                    "sourcepage": "a.txt",
                    "sourcefile": "a.txt",
                    "content": "This is a test document.",
                    "embedding": [],
                    "category": None,
                    "id": "file-a_txt-7465737420646F63756D656E742E706422",
                    "oids": [],
                    "@search.score": 0.03279569745063782,
                    "@search.reranker_score": 3.4577205181121826,
                },
                {
                    "sourcepage": "a.txt",
                    "sourcefile": "a.txt",
                    "content": "This is a test document.",
                    "embedding": [],
                    "category": None,
                    "id": "file-a_txt-7465737420646F63756D656E742E706433",
                    "oids": ["OID_X", "OID_Y"],
                    "@search.score": 0.03279569745063782,
                    "@search.reranker_score": 3.4577205181121826,
                },
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

    response = await auth_client.post(
        "/delete_uploaded", headers={"Authorization": "Bearer test"}, json={"filename": "a.txt"}
    )
    assert response.status_code == 200
    assert len(searched_filters) == 2, "It should have searched twice (with no results on second try)"
    assert searched_filters[0] == "sourcefile eq 'a.txt'"
    assert len(deleted_documents) == 1, "It should have only deleted the document solely owned by OID_X"
    assert deleted_documents[0]["id"] == "file-a_txt-7465737420646F63756D656E742E706466"
