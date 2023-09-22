import pytest
from azure.search.documents.aio import SearchClient
from conftest import MockAzureCredential
from scripts.manageacl import ManageAcl


class AsyncSearchResultsIterator:
    def __init__(self, results):
        self.results = results
        self.num = len(results)

    def __aiter__(self):
        return self

    async def __anext__(self):
        self.num -= 1
        if self.num >= 0:
            return self.results[self.num]

        raise StopAsyncIteration


@pytest.mark.asyncio
async def test_view_acl(monkeypatch, capsys):
    async def mock_search(self, *args, **kwargs):
        assert kwargs.get("filter") == "sourcefile eq 'a.txt'"
        assert kwargs.get("select") == ["id", "oids"]
        return AsyncSearchResultsIterator([{"oids": ["OID_ACL"]}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        document="a.txt",
        acl_action="view",
        acl_type="oids",
        acl="",
        credentials=MockAzureCredential(),
    )
    await command.run()
    captured = capsys.readouterr()
    assert captured.out.strip() == '["OID_ACL"]'
