import logging

import pytest
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from .mocks import MockAzureCredential
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
        assert kwargs.get("filter") == "storageUrl eq 'https://test.blob.core.windows.net/content/a.txt'"
        assert kwargs.get("select") == ["id", "oids"]
        return AsyncSearchResultsIterator([{"oids": ["OID_ACL"]}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="https://test.blob.core.windows.net/content/a.txt",
        acl_action="view",
        acl_type="oids",
        acl="",
        credentials=MockAzureCredential(),
    )
    await command.run()
    captured = capsys.readouterr()
    assert captured.out.strip() == '["OID_ACL"]'


@pytest.mark.asyncio
async def test_remove_acl(monkeypatch, capsys):
    async def mock_search(self, *args, **kwargs):
        assert kwargs.get("filter") == "storageUrl eq 'https://test.blob.core.windows.net/content/a.txt'"
        assert kwargs.get("select") == ["id", "oids"]
        return AsyncSearchResultsIterator(
            [
                {"id": 1, "oids": ["OID_ACL_TO_KEEP", "OID_ACL_TO_REMOVE"]},
                {"id": 2, "oids": ["OID_ACL_TO_KEEP", "OID_ACL_TO_REMOVE"]},
            ]
        )

    merged_documents = []

    async def mock_merge_documents(self, *args, **kwargs):
        for document in kwargs.get("documents"):
            merged_documents.append(document)

    monkeypatch.setattr(SearchClient, "search", mock_search)
    monkeypatch.setattr(SearchClient, "merge_documents", mock_merge_documents)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="https://test.blob.core.windows.net/content/a.txt",
        acl_action="remove",
        acl_type="oids",
        acl="OID_ACL_TO_REMOVE",
        credentials=MockAzureCredential(),
    )
    await command.run()
    assert merged_documents == [{"id": 2, "oids": ["OID_ACL_TO_KEEP"]}, {"id": 1, "oids": ["OID_ACL_TO_KEEP"]}]


@pytest.mark.asyncio
async def test_remove_all_acl(monkeypatch, capsys):
    async def mock_search(self, *args, **kwargs):
        assert kwargs.get("filter") == "storageUrl eq 'https://test.blob.core.windows.net/content/a.txt'"
        assert kwargs.get("select") == ["id", "oids"]
        return AsyncSearchResultsIterator(
            [
                {"id": 1, "oids": ["OID_ACL_TO_REMOVE", "OID_ACL_TO_REMOVE"]},
                {"id": 2, "oids": ["OID_ACL_TO_REMOVE", "OID_ACL_TO_REMOVE"]},
            ]
        )

    merged_documents = []

    async def mock_merge_documents(self, *args, **kwargs):
        for document in kwargs.get("documents"):
            merged_documents.append(document)

    monkeypatch.setattr(SearchClient, "search", mock_search)
    monkeypatch.setattr(SearchClient, "merge_documents", mock_merge_documents)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="https://test.blob.core.windows.net/content/a.txt",
        acl_action="remove_all",
        acl_type="oids",
        acl="",
        credentials=MockAzureCredential(),
    )
    await command.run()
    assert merged_documents == [{"id": 2, "oids": []}, {"id": 1, "oids": []}]


@pytest.mark.asyncio
async def test_add_acl(monkeypatch, caplog):
    async def mock_search(self, *args, **kwargs):
        assert kwargs.get("filter") == "storageUrl eq 'https://test.blob.core.windows.net/content/a.txt'"
        assert kwargs.get("select") == ["id", "oids"]
        return AsyncSearchResultsIterator([{"id": 1, "oids": ["OID_EXISTS"]}, {"id": 2, "oids": ["OID_EXISTS"]}])

    merged_documents = []

    async def mock_merge_documents(self, *args, **kwargs):
        for document in kwargs.get("documents"):
            merged_documents.append(document)

    monkeypatch.setattr(SearchClient, "search", mock_search)
    monkeypatch.setattr(SearchClient, "merge_documents", mock_merge_documents)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="https://test.blob.core.windows.net/content/a.txt",
        acl_action="add",
        acl_type="oids",
        acl="OID_EXISTS",
        credentials=MockAzureCredential(),
    )
    with caplog.at_level(logging.INFO):
        await command.run()
        assert merged_documents == []
        assert "Search document 1 already has oids acl OID_EXISTS" in caplog.text
        assert "Search document 2 already has oids acl OID_EXISTS" in caplog.text
        assert "Not updating any search documents" in caplog.text

    merged_documents.clear()
    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="https://test.blob.core.windows.net/content/a.txt",
        acl_action="add",
        acl_type="oids",
        acl="OID_ADD",
        credentials=MockAzureCredential(),
    )
    with caplog.at_level(logging.INFO):
        await command.run()
        assert merged_documents == [
            {"id": 2, "oids": ["OID_EXISTS", "OID_ADD"]},
            {"id": 1, "oids": ["OID_EXISTS", "OID_ADD"]},
        ]
        assert "Adding acl OID_ADD to 2 search documents" in caplog.text


@pytest.mark.asyncio
async def test_update_storage_urls(monkeypatch, caplog):
    async def mock_search(self, *args, **kwargs):
        assert kwargs.get("filter") == "storageUrl eq ''"
        assert kwargs.get("select") == ["id", "storageUrl", "oids", "sourcefile"]
        return AsyncSearchResultsIterator(
            [
                {"id": 1, "oids": ["OID_EXISTS"], "storageUrl": "", "sourcefile": "a.txt"},
                {"id": 2, "oids": [], "storageUrl": "", "sourcefile": "ab.txt"},
            ]
        )

    merged_documents = []

    async def mock_merge_documents(self, *args, **kwargs):
        for document in kwargs.get("documents"):
            merged_documents.append(document)

    monkeypatch.setattr(SearchClient, "search", mock_search)
    monkeypatch.setattr(SearchClient, "merge_documents", mock_merge_documents)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="https://test.blob.core.windows.net/content/",
        acl_action="update_storage_urls",
        acl_type="",
        acl="",
        credentials=MockAzureCredential(),
    )
    with caplog.at_level(logging.INFO):
        await command.run()
        assert merged_documents == [{"id": 2, "storageUrl": "https://test.blob.core.windows.net/content/ab.txt"}]
        assert "Not updating storage URL of document 1 as it has only one oid and may be user uploaded" in caplog.text
        assert "Adding storage URL https://test.blob.core.windows.net/content/ab.txt for document 2" in caplog.text
        assert "Updating storage URL for 1 search documents" in caplog.text


@pytest.mark.asyncio
async def test_enable_acls_with_missing_fields(monkeypatch, capsys):
    async def mock_get_index(self, *args, **kwargs):
        return SearchIndex(name="INDEX", fields=[])

    updated_index = []

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_index.append(index)

    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="",
        acl_action="enable_acls",
        acl_type="",
        acl="",
        credentials=MockAzureCredential(),
    )
    await command.run()
    assert len(updated_index) == 1
    index = updated_index[0]
    validate_index(index)


@pytest.mark.asyncio
async def test_enable_acls_without_missing_fields(monkeypatch, capsys):
    async def mock_get_index(self, *args, **kwargs):
        return SearchIndex(
            name="INDEX",
            fields=[
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

    updated_index = []

    async def mock_create_or_update_index(self, index, *args, **kwargs):
        updated_index.append(index)

    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)
    monkeypatch.setattr(SearchIndexClient, "create_or_update_index", mock_create_or_update_index)

    command = ManageAcl(
        service_name="SERVICE",
        index_name="INDEX",
        url="",
        acl_action="enable_acls",
        acl_type="",
        acl="",
        credentials=MockAzureCredential(),
    )
    await command.run()
    assert len(updated_index) == 1
    index = updated_index[0]
    validate_index(index)


def validate_index(index):
    assert len(index.fields) == 3
    oids_field = None
    groups_field = None
    storageurl_field = None
    for field in index.fields:
        if field.name == "oids":
            assert not oids_field
            oids_field = field
        elif field.name == "groups":
            assert not groups_field
            groups_field = field
        elif field.name == "storageUrl":
            storageurl_field = field

    assert oids_field and groups_field and storageurl_field
    assert oids_field.type == SearchFieldDataType.Collection(
        SearchFieldDataType.String
    ) and groups_field.type == SearchFieldDataType.Collection(SearchFieldDataType.String)
    assert storageurl_field.type == SearchFieldDataType.String
    assert oids_field.filterable and groups_field.filterable and storageurl_field.filterable
