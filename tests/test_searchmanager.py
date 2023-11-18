import io

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

from scripts.prepdocslib.listfilestrategy import File
from scripts.prepdocslib.searchmanager import SearchManager, Section
from scripts.prepdocslib.strategy import SearchInfo
from scripts.prepdocslib.textsplitter import SplitPage


@pytest.mark.asyncio
async def test_update_content(monkeypatch):
    async def mock_upload_documents(self, documents):
        assert len(documents) == 1
        assert documents[0]["id"] == "file-foo_pdf-666F6F2E706466-page-0"
        assert documents[0]["content"] == "test content"
        assert documents[0]["category"] == "test"
        assert documents[0]["sourcepage"] == "foo.pdf#page=1"
        assert documents[0]["sourcefile"] == "foo.pdf"

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    manager = SearchManager(
        SearchInfo(
            endpoint="https://testsearchclient.blob.core.windows.net",
            credential=AzureKeyCredential("test"),
            index_name="test",
            verbose=True,
        )
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
async def test_update_content_many(monkeypatch):
    ids = []

    async def mock_upload_documents(self, documents):
        ids.extend([doc["id"] for doc in documents])

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    manager = SearchManager(
        SearchInfo(
            endpoint="https://testsearchclient.blob.core.windows.net",
            credential=AzureKeyCredential("test"),
            index_name="test",
            verbose=True,
        )
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
