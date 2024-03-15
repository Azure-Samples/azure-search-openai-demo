import azure.storage.filedatalake.aio
import pytest
from azure.search.documents.aio import SearchClient


@pytest.mark.asyncio
async def test_list_uploaded(auth_client, monkeypatch, mock_data_lake_service_client):
    response = await auth_client.get("/list_uploaded", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert (await response.get_json()) == ["a.txt", "b.txt", "c.txt"]


@pytest.mark.asyncio
async def test_delete_uploaded(auth_client, monkeypatch, mock_data_lake_service_client):

    async def mock_delete_file(self):
        return None

    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "delete_file", mock_delete_file)

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
